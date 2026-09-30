#!/usr/bin/env python3
"""
Fetch REAL daily data from yfinance and load into the stock_prices table.
Uses sleep() throttling to avoid API spamming.

Modes:
  python3 fetch_real_yfinance_data.py               # full universe (real_tickers.json)
  python3 fetch_real_yfinance_data.py --smoke       # smoke test: 15 tickers, real pull path
  python3 fetch_real_yfinance_data.py --tickers AAPL,MSFT
  python3 fetch_real_yfinance_data.py --smoke --days 250 --no-clear
"""
import json
import psycopg2
from psycopg2.extras import execute_batch
import yfinance as yf
import pandas as pd
import time
import argparse
from datetime import datetime, timedelta

DB_CONFIG = {
    "host": "localhost",
    "database": "stock_data",
    "user": "postgres",
    "password": "stock_password",
    "port": 5432,
}

# Small, liquid universe for smoke tests: exercises the real yfinance
# pull path (fetch_ticker_data + insert_batch) without the full 2413-ticker run.
SMOKE_TICKERS = [
    'AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMZN', 'META', 'GOOGL',
    'JPM', 'JNJ', 'V', 'XOM', 'PG', 'KO', 'NFLX', 'AMD',
]

# Strategies need ~200 trading days of history (SMA-200), so the default
# window covers ~400 calendar days ending today.
DEFAULT_LOOKBACK_DAYS = 400

class RealDataFetcher:
    """Fetch and load real daily data from yfinance"""

    def __init__(self, tickers=None, start_date=None, end_date=None,
                 lookback_days=DEFAULT_LOOKBACK_DAYS,
                 sleep_seconds=0.5, clear=True):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.cursor = self.conn.cursor()
        end = end_date or datetime.now().strftime("%Y-%m-%d")
        start = start_date or (datetime.now() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
        self.start_date = start
        self.end_date = end
        self.sleep_seconds = sleep_seconds
        self.clear = clear
        # Explicit list wins; otherwise load the full universe from disk.
        self.tickers = tickers if tickers is not None else self.load_tickers()
    
    def close(self):
        if self.conn:
            self.cursor.close()
            self.conn.close()
    
    def load_tickers(self):
        """Load real tickers from real_tickers.json, falling back to the
        smoke-test universe if the file is missing."""
        try:
            with open('real_tickers.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print("⚠ real_tickers.json not found — falling back to SMOKE_TICKERS")
            return list(SMOKE_TICKERS)
        except Exception as e:
            print(f"Error loading real_tickers.json: {e}")
            return []
    
    def clear_database(self):
        """Truncate existing (synthetic) data"""
        print("Clearing old synthetic data...")
        self.cursor.execute("TRUNCATE stock_prices CASCADE;")
        self.conn.commit()
        print("✓ Database cleared")
    
    def fetch_ticker_data(self, ticker):
        """Fetch real data for a single ticker"""
        try:
            # Fetch from yfinance
            data = yf.download(
                ticker,
                start=self.start_date,
                end=self.end_date,
                progress=False,  # Suppress progress bars
                interval="1d"
            )
            
            if data.empty or len(data) < 10:
                return None  # Not enough data
            
            # Handle MultiIndex columns (yfinance returns ('Price', 'TICKER'))
            # Flatten to single-level columns if needed
            if isinstance(data.columns, pd.MultiIndex):
                # For single ticker: columns are like ('Open', 'AAPL'), ('Close', 'AAPL'), etc.
                # We want to access just the ticker's data
                data.columns = data.columns.get_level_values(0)
            
            # Convert to list of tuples: (ticker, date, open, high, low, close, volume)
            records = []
            for idx, row in data.iterrows():
                try:
                    o = float(row['Open'])
                    h = float(row['High'])
                    l = float(row['Low'])
                    c = float(row['Close'])
                    v = int(row['Volume'])
                    
                    records.append((ticker, idx.date(), o, h, l, c, v))
                except (ValueError, TypeError):
                    # Skip malformed rows
                    continue
            
            return records if records else None
        except Exception as e:
            print(f"  ⚠ {ticker}: {str(e)[:50]}")
            return None
    
    def insert_batch(self, records):
        """Insert batch of records into database"""
        if not records:
            return 0
        
        try:
            insert_sql = """
                INSERT INTO stock_prices (ticker, timestamp, open, high, low, close, volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ticker, timestamp) DO NOTHING;
            """
            
            execute_batch(self.cursor, insert_sql, records, page_size=5000)
            self.conn.commit()
            return len(records)
        except Exception as e:
            print(f"  ✗ Insert error: {e}")
            self.conn.rollback()
            return 0
    
    def fetch_all(self):
        """Fetch and load real data for all tickers"""
        print("="*80)
        print("REAL DATA FETCHER: yfinance Daily Data")
        print("="*80)
        print(f"Period: {self.start_date} to {self.end_date}")
        print(f"Sleep throttle: {self.sleep_seconds}s between requests\n")

        # Clear old data
        if self.clear:
            self.clear_database()

        # Ticker list
        tickers = self.tickers
        print(f"Loading {len(tickers)} tickers...\n")
        
        if not tickers:
            print("❌ No tickers loaded")
            return False
        
        # Fetch and insert
        total_inserted = 0
        success_count = 0
        failed_count = 0
        batch_buffer = []
        batch_size = 100  # Insert every 100 tickers
        cleared = False

        for i, ticker in enumerate(tickers):
            progress = f"[{i+1:4d}/{len(tickers)}]"
            print(f"{progress} Fetching {ticker}...", end=" ", flush=True)

            # Fetch data
            records = self.fetch_ticker_data(ticker)

            if records:
                # Only wipe old data once we've proven the pull works —
                # a failed run shouldn't nuke a good table.
                if self.clear and not cleared:
                    self.clear_database()
                    cleared = True
                batch_buffer.extend(records)
                print(f"✓ {len(records)} bars")
                success_count += 1
            else:
                print("⚠ No data")
                failed_count += 1
            
            # Insert when batch reaches threshold
            if len(batch_buffer) >= 50000:  # ~50k records per batch
                inserted = self.insert_batch(batch_buffer)
                total_inserted += inserted
                print(f"  [BATCH INSERT: {inserted} records]")
                batch_buffer = []
            
            # Throttle API requests
            time.sleep(self.sleep_seconds)
        
        # Insert remaining
        if batch_buffer:
            inserted = self.insert_batch(batch_buffer)
            total_inserted += inserted
            print(f"[FINAL BATCH INSERT: {inserted} records]")
        
        # Verify
        self.cursor.execute("""
            SELECT COUNT(*) as total, COUNT(DISTINCT ticker) as unique_tickers,
                   MIN(timestamp) as start_date, MAX(timestamp) as end_date
            FROM stock_prices
        """)
        result = self.cursor.fetchone()
        
        print("\n" + "="*80)
        print("REAL DATA LOAD COMPLETE")
        print("="*80)
        print(f"✓ Successfully fetched: {success_count} tickers")
        print(f"✗ Failed: {failed_count} tickers")
        print(f"✓ Total records inserted: {total_inserted:,}")
        print(f"✓ Unique tickers in DB: {result[1]}")
        print(f"✓ Date range: {result[2]} to {result[3]}")
        
        return success_count > 0

def parse_args():
    p = argparse.ArgumentParser(
        description="Fetch real daily OHLCV data from yfinance into stock_prices.")
    p.add_argument('--smoke', action='store_true',
                   help=f"Smoke test: fetch only {len(SMOKE_TICKERS)} tickers "
                        "through the real pull path.")
    p.add_argument('--tickers', default=None,
                   help="Comma-separated ticker list (overrides file/smoke).")
    p.add_argument('--days', type=int, default=DEFAULT_LOOKBACK_DAYS,
                   help=f"Lookback window in days (default {DEFAULT_LOOKBACK_DAYS}).")
    p.add_argument('--no-clear', action='store_true',
                   help="Don't truncate stock_prices before loading.")
    return p.parse_args()

if __name__ == '__main__':
    args = parse_args()

    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(',') if t.strip()]
    elif args.smoke:
        tickers = list(SMOKE_TICKERS)
    else:
        tickers = None  # load full universe from real_tickers.json

    fetcher = RealDataFetcher(tickers=tickers, lookback_days=args.days,
                              clear=not args.no_clear)
    success = fetcher.fetch_all()
    fetcher.close()

    if success:
        print("\n✅ Real data ready for SURGE and ANCHOR strategies")
    else:
        print("\n❌ Data fetch failed")
