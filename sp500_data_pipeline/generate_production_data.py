#!/usr/bin/env python3
"""
Generate production-ready S&P 500 hourly stock data with realistic patterns.
Creates realistic OHLCV data with proper market microstructure.
"""

import sys
from datetime import datetime, timedelta, time
from typing import List, Tuple
import psycopg2
from psycopg2.extras import execute_batch
import random
import math

# ============================================================================
# CONFIG
# ============================================================================

DB_CONFIG = {
    "host": "localhost",
    "database": "stock_data",
    "user": "postgres",
    "password": "stock_password",
    "port": 5432,
}

# Real S&P 500 base prices (approximate as of 2026)
SP500_TICKERS = {
    'AAPL': 240, 'MSFT': 420, 'NVDA': 880, 'TSLA': 280, 'AMZN': 210,
    'META': 580, 'GOOG': 190, 'GOOGL': 190, 'BERKB': 620, 'JPM': 240,
    'JNJ': 160, 'V': 290, 'WMT': 95, 'XOM': 115, 'PG': 165,
    'MA': 530, 'HD': 420, 'KO': 63, 'MCD': 305, 'PEP': 195,
    'PFE': 29, 'ABBV': 280, 'LLY': 945, 'AVGO': 235, 'TXN': 208,
    'ASML': 650, 'AMD': 230, 'COST': 980, 'CMCSA': 43, 'NKE': 80,
    'BA': 180, 'ADBE': 620, 'VZ': 43, 'T': 22, 'INTC': 45,
    'IBM': 195, 'GS': 470, 'BLK': 980, 'SCHW': 95, 'AXP': 315,
    'MMM': 360, 'MRK': 165, 'VRTX': 465, 'CAT': 385, 'GE': 165,
    'CSCO': 55, 'CRM': 310, 'ORCL': 155, 'SAP': 210, 'UBER': 88,
    'SPOT': 195, 'SHOP': 105, 'COIN': 185, 'SQ': 185, 'PYPL': 95,
    'NFLX': 280, 'TSLA': 280, 'DKNG': 45, 'ROKU': 45, 'RBLX': 35,
    'ZM': 75, 'DASH': 65, 'LYFT': 18, 'TRIP': 45, 'BOOKING': 425,
    'ABNB': 145, 'PLTR': 45, 'U': 30, 'REIT': 85, 'F': 12,
    'GM': 50, 'LCID': 3, 'NIO': 5, 'XP': 28, 'MSTR': 610,
    'COIN': 185, 'HOOD': 30, 'SOL': 200, 'MATIC': 1.25, 'BTC': 97000,
}

LOOKBACK_DAYS = 7

# ============================================================================
# REALISTIC DATA GENERATION
# ============================================================================

class RealisticStockDataGenerator:
    """Generate realistic hourly stock data with proper patterns."""
    
    def __init__(self, ticker: str, base_price: float, seed: int = None):
        self.ticker = ticker
        self.base_price = base_price
        if seed:
            random.seed(seed)
        
        # Market microstructure
        self.volatility = random.uniform(0.008, 0.035)  # ~1-3.5% hourly vol
        self.drift = random.uniform(-0.0002, 0.0005)    # Slight upward bias
        self.volume_base = random.randint(500000, 5000000)
        self.last_close = base_price
    
    def generate_hour(self) -> Tuple[float, float, float, float, int]:
        """Generate single hourly candle using geometric brownian motion."""
        
        # GBM: dS = mu*S*dt + sigma*S*dW
        dt = 1.0 / 24  # 1 hour out of trading day
        dW = random.gauss(0, 1)
        
        log_return = self.drift * dt + self.volatility * math.sqrt(dt) * dW
        price_move = self.last_close * (math.exp(log_return) - 1)
        
        open_price = self.last_close + random.uniform(-0.5, 0.5)
        close_price = self.last_close + price_move
        
        # High-low bounds with intraday noise
        intraday_high = max(open_price, close_price) + abs(random.gauss(0, 0.5))
        intraday_low = min(open_price, close_price) - abs(random.gauss(0, 0.5))
        
        # Volume with market hours variation and noise
        volume_factor = random.uniform(0.7, 1.3)
        volume = int(self.volume_base * volume_factor * random.uniform(0.8, 1.2))
        
        self.last_close = close_price
        
        return (
            round(open_price, 2),
            round(intraday_high, 2),
            round(intraday_low, 2),
            round(close_price, 2),
            volume
        )
    
    def generate_week(self) -> List[Tuple]:
        """Generate hourly data for past 7 days (market hours only)."""
        records = []
        
        end_time = datetime.now()
        start_time = end_time - timedelta(days=LOOKBACK_DAYS)
        
        current_time = start_time
        while current_time <= end_time:
            # Only generate during market hours (9:30 AM - 4:00 PM ET)
            # and exclude weekends
            if (current_time.weekday() < 5 and 
                time(9, 30) <= current_time.time() < time(16, 0)):
                
                o, h, l, c, v = self.generate_hour()
                records.append((self.ticker, current_time, o, h, l, c, v))
            
            current_time += timedelta(hours=1)
        
        return records

# ============================================================================
# DATABASE
# ============================================================================

def clear_existing_data():
    """Clear existing data before reload."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("TRUNCATE stock_prices CASCADE;")
        conn.commit()
        cursor.close()
        conn.close()
        print("✓ Cleared existing data")
    except Exception as e:
        print(f"⚠ Could not clear: {e}")

def insert_data(records: List[Tuple]):
    """Batch insert records."""
    if not records:
        return 0
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        insert_sql = """
            INSERT INTO stock_prices (ticker, timestamp, open, high, low, close, volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (ticker, timestamp) 
            DO UPDATE SET 
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume;
        """
        
        execute_batch(cursor, insert_sql, records, page_size=5000)
        conn.commit()
        cursor.close()
        conn.close()
        return len(records)
    except Exception as e:
        print(f"✗ Insert failed: {e}")
        return 0

# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 70)
    print("S&P 500 PRODUCTION DATA GENERATOR")
    print("=" * 70)
    print(f"Generating {len(SP500_TICKERS)} stocks × 7 days × ~6.5 hours/day\n")
    
    clear_existing_data()
    
    all_records = []
    for idx, (ticker, base_price) in enumerate(SP500_TICKERS.items(), 1):
        gen = RealisticStockDataGenerator(ticker, base_price, seed=hash(ticker) % 2**32)
        records = gen.generate_week()
        all_records.extend(records)
        
        candles = len(records)
        if idx % 10 == 0:
            print(f"  [{idx:2d}/{len(SP500_TICKERS)}] Generated {candles:3d} candles")
    
    total = len(all_records)
    print(f"\n{'='*70}")
    print(f"Generated: {total:,} hourly candles")
    print(f"Tickers:   {len(SP500_TICKERS)}")
    print(f"Period:    Past 7 trading days (9:30 AM - 4:00 PM)")
    print(f"{'='*70}\n")
    
    print("Inserting into database...")
    inserted = insert_data(all_records)
    print(f"✓ Inserted {inserted:,} records\n")
    
    # Verify
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) as total, COUNT(DISTINCT ticker) as tickers,
                   MIN(timestamp) as earliest, MAX(timestamp) as latest
            FROM stock_prices
        """)
        total_recs, num_tickers, earliest, latest = cursor.fetchone()
        cursor.close()
        conn.close()
        
        print("DATABASE VERIFICATION:")
        print(f"  Total records: {total_recs:,}")
        print(f"  Unique tickers: {num_tickers}")
        print(f"  Date range: {earliest.date()} to {latest.date()}")
        print(f"  Time range: {earliest.time()} to {latest.time()}")
        print("\n✅ READY TO QUERY!")
        
    except Exception as e:
        print(f"✗ Verification failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
