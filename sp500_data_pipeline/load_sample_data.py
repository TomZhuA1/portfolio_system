#!/usr/bin/env python3
"""
Load sample S&P 500 hourly data for demo purposes.
Creates realistic hourly OHLCV data for testing.
"""

import sys
from datetime import datetime, timedelta
from typing import List, Tuple
import psycopg2
from psycopg2.extras import execute_batch
import random

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

# Sample major S&P 500 stocks
SAMPLE_TICKERS = [
    'AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMZN', 'META', 'GOOG',
    'BERKB', 'JPM', 'JNJ', 'V', 'WMT', 'XOM', 'PG', 'MA'
]

# ============================================================================
# DATA GENERATION
# ============================================================================

def generate_hourly_data(ticker: str, days: int = 7) -> List[Tuple]:
    """Generate realistic hourly OHLCV data for a ticker."""
    records = []
    
    # Random base price for this ticker
    base_price = random.uniform(50, 500)
    
    # Generate hourly data for past N days
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    current_time = start_time
    while current_time <= end_time:
        # Skip weekends and after-hours
        if current_time.weekday() < 5 and 9 <= current_time.hour < 16:
            # Random walk for price
            open_price = base_price + random.uniform(-2, 2)
            close_price = open_price + random.uniform(-1.5, 1.5)
            high_price = max(open_price, close_price) + random.uniform(0, 1)
            low_price = min(open_price, close_price) - random.uniform(0, 1)
            volume = random.randint(1000000, 10000000)
            
            records.append((
                ticker,
                current_time,
                round(open_price, 2),
                round(high_price, 2),
                round(low_price, 2),
                round(close_price, 2),
                volume
            ))
            
            # Update base price for next hour (random walk)
            base_price = close_price
        
        current_time += timedelta(hours=1)
    
    return records

# ============================================================================
# DATABASE
# ============================================================================

def insert_data(records: List[Tuple]):
    """Insert sample data into database."""
    if not records:
        return
    
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
        
        execute_batch(cursor, insert_sql, records, page_size=1000)
        conn.commit()
        print(f"✓ Inserted {len(records)} records")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"✗ Insert failed: {e}")
        sys.exit(1)

# ============================================================================
# MAIN
# ============================================================================

def main():
    print("=== Loading Sample S&P 500 Data ===")
    print(f"Tickers: {len(SAMPLE_TICKERS)}")
    print(f"Data: 7 days × ~7 hours/day = ~49 candles/ticker\n")
    
    all_records = []
    for ticker in SAMPLE_TICKERS:
        records = generate_hourly_data(ticker, days=7)
        all_records.extend(records)
        print(f"  {ticker}: {len(records)} candles")
    
    print(f"\nTotal records: {len(all_records)}")
    print("Inserting into database...")
    insert_data(all_records)
    
    print("\n✓ Sample data loaded successfully!")
    print("\nQuick test query:")
    print("  SELECT COUNT(*) as total_records, COUNT(DISTINCT ticker) as tickers")
    print("  FROM stock_prices;")

if __name__ == "__main__":
    main()
