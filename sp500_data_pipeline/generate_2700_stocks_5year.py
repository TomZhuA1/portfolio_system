#!/usr/bin/env python3
"""
Generate 5 years of daily OHLCV data for 2,709 stocks (S&P 500 + Russell 3000).
"""

import sys
import json
import psycopg2
from psycopg2.extras import execute_batch
from datetime import datetime, timedelta
import random
import math

DB_CONFIG = {
    "host": "localhost",
    "database": "stock_data",
    "user": "postgres",
    "password": "stock_password",
    "port": 5432,
}

# Base prices for known stocks
KNOWN_PRICES = {
    'AAPL': 130, 'MSFT': 250, 'NVDA': 450, 'TSLA': 650, 'AMZN': 3200,
    'META': 350, 'GOOG': 2700, 'GOOGL': 2700, 'BERKB': 400, 'JPM': 145,
    'JNJ': 160, 'V': 220, 'WMT': 140, 'XOM': 60, 'PG': 135,
    'MA': 380, 'HD': 310, 'KO': 50, 'MCD': 230, 'PEP': 140,
}

PRICE_RANGES = {
    'micro': (1, 5),
    'small': (5, 50),
    'mid': (50, 200),
    'large': (200, 500),
}

US_HOLIDAYS = {
    datetime(2021, 1, 1), datetime(2021, 1, 18), datetime(2021, 2, 15), datetime(2021, 3, 26),
    datetime(2021, 5, 31), datetime(2021, 7, 5), datetime(2021, 9, 6), datetime(2021, 11, 25),
    datetime(2021, 12, 24), datetime(2022, 1, 17), datetime(2022, 2, 21), datetime(2022, 4, 15),
    datetime(2022, 5, 30), datetime(2022, 7, 4), datetime(2022, 9, 5), datetime(2022, 11, 24),
    datetime(2022, 12, 26), datetime(2023, 1, 16), datetime(2023, 2, 20), datetime(2023, 4, 7),
    datetime(2023, 5, 29), datetime(2023, 7, 4), datetime(2023, 9, 4), datetime(2023, 11, 23),
    datetime(2023, 12, 25), datetime(2024, 1, 15), datetime(2024, 2, 19), datetime(2024, 3, 29),
    datetime(2024, 5, 27), datetime(2024, 7, 4), datetime(2024, 9, 2), datetime(2024, 11, 28),
    datetime(2024, 12, 25), datetime(2025, 1, 20), datetime(2025, 2, 17), datetime(2025, 4, 18),
    datetime(2025, 5, 26), datetime(2025, 7, 4), datetime(2025, 9, 1), datetime(2025, 11, 27),
    datetime(2025, 12, 25), datetime(2026, 1, 19), datetime(2026, 2, 16), datetime(2026, 4, 10),
    datetime(2026, 5, 25), datetime(2026, 7, 3), datetime(2026, 9, 7), datetime(2026, 11, 26),
}

def is_trading_day(date):
    """Check if date is a trading day."""
    if date.weekday() >= 5:
        return False
    return date not in US_HOLIDAYS

class StockDataGen:
    """Generate realistic daily OHLCV data."""
    
    def __init__(self, ticker, base_price=None):
        self.ticker = ticker
        if base_price:
            self.base_price = base_price
        elif ticker in KNOWN_PRICES:
            self.base_price = KNOWN_PRICES[ticker]
        else:
            category = random.choice(list(PRICE_RANGES.keys()))
            low, high = PRICE_RANGES[category]
            self.base_price = random.uniform(low, high)
        
        self.current_price = self.base_price
        self.annual_vol = random.uniform(0.15, 0.45)
        self.daily_vol = self.annual_vol / math.sqrt(252)
        self.drift = random.uniform(0.05, 0.25) / 252
    
    def gen_day(self):
        """Generate one day of OHLCV."""
        dt = 1.0 / 252
        dW = random.gauss(0, 1)
        log_ret = (self.drift - 0.5 * self.daily_vol ** 2) * dt + self.daily_vol * math.sqrt(dt) * dW
        daily_ret = math.exp(log_ret) - 1
        
        open_p = self.current_price
        close_p = open_p * (1 + daily_ret)
        high_p = max(open_p, close_p) * (1 + abs(random.gauss(0, 0.005)))
        low_p = min(open_p, close_p) * (1 - abs(random.gauss(0, 0.005)))
        
        volume = int(random.randint(100000, 5000000) * random.uniform(0.8, 1.2))
        
        self.current_price = close_p
        
        return (round(open_p, 2), round(high_p, 2), round(low_p, 2), round(close_p, 2), volume)
    
    def gen_5years(self):
        """Generate 5 years of daily data."""
        records = []
        end = datetime(2026, 2, 1)
        start = end - timedelta(days=5*365)
        
        current = start
        while current <= end:
            if is_trading_day(current):
                o, h, l, c, v = self.gen_day()
                records.append((self.ticker, current, o, h, l, c, v))
            current += timedelta(days=1)
        
        return records

def clear_db():
    """Clear old data."""
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("TRUNCATE stock_prices CASCADE;")
    conn.commit()
    cursor.close()
    conn.close()
    print("✓ Cleared database")

def insert_batch(records):
    """Insert records."""
    if not records:
        return 0
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    sql = """
        INSERT INTO stock_prices (ticker, timestamp, open, high, low, close, volume)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (ticker, timestamp) DO NOTHING;
    """
    
    execute_batch(cursor, sql, records, page_size=10000)
    conn.commit()
    count = len(records)
    cursor.close()
    conn.close()
    return count

def main():
    print("=" * 80)
    print("GENERATE 2,709 STOCKS × 5 YEARS OF DAILY DATA")
    print("=" * 80)
    
    # Load tickers
    print("\nLoading 2,709 tickers...")
    with open('all_tickers.json', 'r') as f:
        tickers = json.load(f)
    print(f"✓ Loaded {len(tickers)} tickers")
    
    # Clear
    clear_db()
    
    # Generate and insert
    print(f"\nGenerating data for {len(tickers)} stocks...\n")
    
    total = 0
    batch = []
    batch_size = 50
    
    for idx, ticker in enumerate(tickers, 1):
        gen = StockDataGen(ticker)
        records = gen.gen_5years()
        batch.extend(records)
        
        if idx % batch_size == 0 or idx == len(tickers):
            inserted = insert_batch(batch)
            total += inserted
            batch = []
            pct = (idx / len(tickers)) * 100
            print(f"  [{idx:4d}/{len(tickers)}] {pct:5.1f}% | Total inserted: {total:,}")
    
    # Verify
    print("\n" + "=" * 80)
    print("VERIFICATION")
    print("=" * 80)
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as total, COUNT(DISTINCT ticker) as tickers, MIN(timestamp) as earliest, MAX(timestamp) as latest FROM stock_prices")
    total_recs, num_tickers, earliest, latest = cursor.fetchone()
    
    print(f"\n✓ Total records: {total_recs:,}")
    print(f"✓ Unique stocks: {num_tickers}")
    print(f"✓ Date range: {earliest.date()} to {latest.date()}")
    
    cursor.close()
    conn.close()
    
    print("\n✅ COMPLETE!")

if __name__ == "__main__":
    main()
