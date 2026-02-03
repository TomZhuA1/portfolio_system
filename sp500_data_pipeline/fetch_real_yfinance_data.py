#!/usr/bin/env python3
"""
Fetch REAL 5-year daily data from yfinance for all 2413 tickers.
Uses sleep() throttling to avoid API spamming.
Replaces synthetic data entirely.
"""
import json
import psycopg2
from psycopg2.extras import execute_batch
import yfinance as yf
import pandas as pd
import time
from datetime import datetime, timedelta

DB_CONFIG = {
    "host": "localhost",
    "database": "stock_data",
    "user": "postgres",
    "password": "stock_password",
    "port": 5432,
}

class RealDataFetcher:
    """Fetch and load real 5-year daily data from yfinance"""
    
    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.cursor = self.conn.cursor()
        self.start_date = "2021-02-02"
        self.end_date = "2026-01-31"
        self.sleep_seconds = 0.5  # Sleep 500ms between requests to avoid rate limiting
    
    def close(self):
        if self.conn:
            self.cursor.close()
            self.conn.close()
    
    def load_tickers(self):
        """Load 2413 real tickers from real_tickers.json"""
        try:
            with open('real_tickers.json', 'r') as f:
                return json.load(f)
        except:
            print("Error loading real_tickers.json")
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
        print("REAL DATA FETCHER: 5-Year yfinance Data")
        print("="*80)
        print(f"Period: {self.start_date} to {self.end_date}")
        print(f"Sleep throttle: {self.sleep_seconds}s between requests\n")
        
        # Clear old synthetic data
        self.clear_database()
        
        # Load ticker list
        tickers = self.load_tickers()
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
        
        for i, ticker in enumerate(tickers):
            progress = f"[{i+1:4d}/{len(tickers)}]"
            print(f"{progress} Fetching {ticker}...", end=" ", flush=True)
            
            # Fetch data
            records = self.fetch_ticker_data(ticker)
            
            if records:
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

if __name__ == '__main__':
    fetcher = RealDataFetcher()
    success = fetcher.fetch_all()
    fetcher.close()
    
    if success:
        print("\n✅ Real data ready for SURGE and ANCHOR strategies")
    else:
        print("\n❌ Data fetch failed")
