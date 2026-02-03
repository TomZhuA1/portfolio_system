#!/usr/bin/env python3
"""
Generate 5 years of daily OHLCV data for S&P 500 + Russell 3000 union.
Realistic market data with proper volatility, gaps, and volume patterns.
Total: ~3000 stocks × ~1250 trading days = 3.75M+ records
"""

import sys
import json
import psycopg2
from psycopg2.extras import execute_batch
from datetime import datetime, timedelta
import random
import math
import os

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

# Real base prices for major stocks (approximate 2021 levels for 5-year backfill)
STOCK_BASE_PRICES = {
    'AAPL': 130, 'MSFT': 250, 'NVDA': 450, 'TSLA': 650, 'AMZN': 3200,
    'META': 350, 'GOOG': 2700, 'GOOGL': 2700, 'BERKB': 400, 'JPM': 145,
    'JNJ': 160, 'V': 220, 'WMT': 140, 'XOM': 60, 'PG': 135,
    'MA': 380, 'HD': 310, 'KO': 50, 'MCD': 230, 'PEP': 140,
}

# For others, use random price in typical ranges
PRICE_RANGES = {
    'micro': (1, 5),           # Penny stocks
    'small': (5, 50),          # Small cap
    'mid': (50, 200),          # Mid cap
    'large': (200, 500),       # Large cap
}

# ============================================================================
# US HOLIDAY CALENDAR (simplest version)
# ============================================================================

US_HOLIDAYS_2021_2026 = {
    # 2021
    datetime(2021, 1, 1),   # New Year
    datetime(2021, 1, 18),  # MLK Day
    datetime(2021, 2, 15),  # Presidents Day
    datetime(2021, 3, 26),  # Good Friday
    datetime(2021, 5, 31),  # Memorial Day
    datetime(2021, 7, 5),   # Independence Day (observed)
    datetime(2021, 9, 6),   # Labor Day
    datetime(2021, 11, 25), # Thanksgiving
    datetime(2021, 12, 24), # Christmas Eve
    # 2022
    datetime(2022, 1, 17),  # MLK Day
    datetime(2022, 2, 21),  # Presidents Day
    datetime(2022, 4, 15),  # Good Friday
    datetime(2022, 5, 30),  # Memorial Day
    datetime(2022, 7, 4),   # Independence Day
    datetime(2022, 9, 5),   # Labor Day
    datetime(2022, 11, 24), # Thanksgiving
    datetime(2022, 12, 26), # Christmas (observed)
    # 2023
    datetime(2023, 1, 16),  # MLK Day
    datetime(2023, 2, 20),  # Presidents Day
    datetime(2023, 4, 7),   # Good Friday
    datetime(2023, 5, 29),  # Memorial Day
    datetime(2023, 7, 4),   # Independence Day
    datetime(2023, 9, 4),   # Labor Day
    datetime(2023, 11, 23), # Thanksgiving
    datetime(2023, 12, 25), # Christmas
    # 2024
    datetime(2024, 1, 15),  # MLK Day
    datetime(2024, 2, 19),  # Presidents Day
    datetime(2024, 3, 29),  # Good Friday
    datetime(2024, 5, 27),  # Memorial Day
    datetime(2024, 7, 4),   # Independence Day
    datetime(2024, 9, 2),   # Labor Day
    datetime(2024, 11, 28), # Thanksgiving
    datetime(2024, 12, 25), # Christmas
    # 2025
    datetime(2025, 1, 20),  # MLK Day
    datetime(2025, 2, 17),  # Presidents Day
    datetime(2025, 4, 18),  # Good Friday
    datetime(2025, 5, 26),  # Memorial Day
    datetime(2025, 7, 4),   # Independence Day
    datetime(2025, 9, 1),   # Labor Day
    datetime(2025, 11, 27), # Thanksgiving
    datetime(2025, 12, 25), # Christmas
    # 2026
    datetime(2026, 1, 19),  # MLK Day
    datetime(2026, 2, 16),  # Presidents Day
    datetime(2026, 4, 10),  # Good Friday
    datetime(2026, 5, 25),  # Memorial Day
    datetime(2026, 7, 3),   # Independence Day (observed)
    datetime(2026, 9, 7),   # Labor Day
    datetime(2026, 11, 26), # Thanksgiving
    datetime(2026, 12, 25), # Christmas
}

def is_trading_day(date):
    """Check if date is a US trading day (weekday, not holiday)."""
    if date.weekday() >= 5:  # Saturday=5, Sunday=6
        return False
    return date not in US_HOLIDAYS_2021_2026

# ============================================================================
# DATA GENERATION
# ============================================================================

class DailyStockDataGenerator:
    """Generate realistic daily OHLCV data with proper market microstructure."""
    
    def __init__(self, ticker: str, base_price: float = None, seed: int = None):
        self.ticker = ticker
        if seed:
            random.seed(seed)
        
        # Get or generate base price
        if base_price:
            self.base_price = base_price
        elif ticker in STOCK_BASE_PRICES:
            self.base_price = STOCK_BASE_PRICES[ticker]
        else:
            # Assign random price based on categories
            category = random.choice(list(PRICE_RANGES.keys()))
            low, high = PRICE_RANGES[category]
            self.base_price = random.uniform(low, high)
        
        # Market microstructure
        self.current_price = self.base_price
        self.annual_volatility = random.uniform(0.15, 0.45)  # 15-45% annual
        self.daily_vol = self.annual_volatility / math.sqrt(252)  # Convert to daily
        self.drift = random.uniform(0.05, 0.25) / 252  # 5-25% annual drift
        self.volume_base = random.randint(100000, 10000000)
        self.volume_trend = random.uniform(0.95, 1.05)
    
    def generate_day(self) -> tuple:
        """Generate single daily bar using GBM."""
        
        # Geometric Brownian Motion
        dt = 1.0 / 252  # 1 day
        dW = random.gauss(0, 1)
        log_return = (self.drift - 0.5 * self.daily_vol ** 2) * dt + self.daily_vol * math.sqrt(dt) * dW
        
        daily_return = math.exp(log_return) - 1
        open_price = self.current_price
        close_price = open_price * (1 + daily_return)
        
        # High-low with intraday movement
        high_price = max(open_price, close_price) * (1 + abs(random.gauss(0, 0.005)))
        low_price = min(open_price, close_price) * (1 - abs(random.gauss(0, 0.005)))
        
        # Volume with seasonal variations
        volume_factor = random.uniform(0.5, 1.5)
        volume = int(self.volume_base * volume_factor * self.volume_trend)
        
        self.current_price = close_price
        self.volume_trend *= random.uniform(0.99, 1.01)  # Slow drift
        
        return (
            round(open_price, 2),
            round(high_price, 2),
            round(low_price, 2),
            round(close_price, 2),
            volume
        )
    
    def generate_5years(self) -> list:
        """Generate daily data for past 5 years (trading days only)."""
        records = []
        
        end_date = datetime(2026, 2, 1)  # Current date
        start_date = end_date - timedelta(days=5*365)
        
        current_date = start_date
        while current_date <= end_date:
            if is_trading_day(current_date):
                o, h, l, c, v = self.generate_day()
                records.append((self.ticker, current_date, o, h, l, c, v))
            
            current_date += timedelta(days=1)
        
        return records

# ============================================================================
# DATABASE
# ============================================================================

def clear_database():
    """Truncate existing data."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("TRUNCATE stock_prices CASCADE;")
        conn.commit()
        cursor.close()
        conn.close()
        print("✓ Cleared existing data")
        return True
    except Exception as e:
        print(f"⚠ Error clearing data: {e}")
        return False

def insert_batch(records: list) -> int:
    """Insert batch of records."""
    if not records:
        return 0
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        insert_sql = """
            INSERT INTO stock_prices (ticker, timestamp, open, high, low, close, volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (ticker, timestamp) DO NOTHING;
        """
        
        execute_batch(cursor, insert_sql, records, page_size=10000)
        conn.commit()
        count = len(records)
        cursor.close()
        conn.close()
        return count
    except Exception as e:
        print(f"✗ Insert failed: {e}")
        return 0

# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=" * 80)
    print("S&P 500 + RUSSELL 3000 - 5 YEAR DAILY DATA GENERATOR")
    print("=" * 80)
    
    # Load ticker list
    print("\nLoading ticker list...")
    try:
        with open('real_tickers.json', 'r') as f:
            tickers = json.load(f)
    except:
        print("Couldn't load from real_tickers.json, trying get_russell_sp500_tickers.py...")
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("ticker_module", 'get_russell_sp500_tickers.py')
            ticker_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(ticker_module)
            tickers = ticker_module.get_union_tickers()
        except:
            print("Couldn't load from file, using hardcoded list")
            tickers = sorted(list(STOCK_BASE_PRICES.keys()) + [
                'SPY', 'QQQ', 'IWM', 'DIA', 'EEM', 'TLT', 'AGG', 'GLD', 'USO', 'TIPS'
            ])
    
    print(f"✓ Loaded {len(tickers)} tickers")
    print(f"  Sample: {tickers[:10]}")
    
    # Calculate expected size
    trading_days = sum(1 for d in range(5*365) if is_trading_day(datetime(2021, 1, 1) + timedelta(days=d)))
    expected_records = len(tickers) * trading_days
    print(f"\nExpected records: {len(tickers)} stocks × ~{trading_days} trading days = ~{expected_records:,}")
    
    # Clear old data
    if not clear_database():
        sys.exit(1)
    
    # Generate and insert
    print(f"\nGenerating and inserting data in batches...")
    print("-" * 80)
    
    total_inserted = 0
    batch_size = 50  # Process 50 stocks at a time
    all_records = []
    
    for idx, ticker in enumerate(tickers, 1):
        gen = DailyStockDataGenerator(ticker, seed=hash(ticker) % 2**32)
        records = gen.generate_5years()
        all_records.extend(records)
        
        # Insert in batches of N stocks worth of data
        if idx % batch_size == 0 or idx == len(tickers):
            inserted = insert_batch(all_records)
            total_inserted += inserted
            all_records = []
            
            pct = (idx / len(tickers)) * 100
            print(f"  [{idx:4d}/{len(tickers)}] {pct:5.1f}% | Inserted: {total_inserted:,} records")
    
    # Final insert
    if all_records:
        inserted = insert_batch(all_records)
        total_inserted += inserted
    
    print("-" * 80)
    print(f"\n✓ Total records inserted: {total_inserted:,}")
    
    # Verify
    print("\nVerifying database...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as total, COUNT(DISTINCT ticker) as tickers, MIN(timestamp) as earliest, MAX(timestamp) as latest FROM stock_prices")
        total_recs, num_tickers, earliest, latest = cursor.fetchone()
        
        print(f"  Total records: {total_recs:,}")
        print(f"  Unique tickers: {num_tickers}")
        print(f"  Date range: {earliest.date()} to {latest.date()}")
        print(f"  Days covered: {(latest.date() - earliest.date()).days}")
        
        # Sample stats
        cursor.execute("SELECT ticker, COUNT(*) as bars FROM stock_prices GROUP BY ticker LIMIT 5")
        print(f"\n  Sample coverage:")
        for ticker, bars in cursor.fetchall():
            print(f"    {ticker}: {bars} daily bars (~{bars/252:.1f} years)")
        
        cursor.close()
        conn.close()
        
        print("\n✅ DATABASE READY!")
        print("\nQuick query:")
        print("  sudo -u postgres psql stock_data -c \"SELECT COUNT(*) FROM stock_prices;\"")
        
    except Exception as e:
        print(f"✗ Verification failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
