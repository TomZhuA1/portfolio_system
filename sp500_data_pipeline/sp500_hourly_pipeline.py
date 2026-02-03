#!/usr/bin/env python3
"""
S&P 500 Hourly Stock Data Pipeline
Pulls hourly OHLCV data for past 7 days for all S&P 500 constituents.
Stores in PostgreSQL with upsert logic for idempotency.
"""

import sys
import logging
from datetime import datetime, timedelta
from typing import List, Tuple
import psycopg2
from psycopg2.extras import execute_batch
import yfinance as yf
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed

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

BATCH_SIZE = 50  # Number of concurrent ticker fetches
MAX_WORKERS = 8  # Thread pool size
LOOKBACK_DAYS = 7

# ============================================================================
# LOGGING
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ============================================================================
# DATABASE
# ============================================================================


def init_db():
    """Create database and schema if not exists."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cursor = conn.cursor()

        # Create schema
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS stock_prices (
                id SERIAL PRIMARY KEY,
                ticker VARCHAR(10) NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                open FLOAT NOT NULL,
                high FLOAT NOT NULL,
                low FLOAT NOT NULL,
                close FLOAT NOT NULL,
                volume BIGINT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(ticker, timestamp)
            );
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_ticker_timestamp ON stock_prices(ticker, timestamp);"
        )
        logger.info("Database initialized")
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"DB init failed: {e}")
        sys.exit(1)


def insert_prices(data: List[Tuple]):
    """Insert or update stock prices (upsert)."""
    if not data:
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
                volume = EXCLUDED.volume,
                created_at = NOW();
        """
        execute_batch(cursor, insert_sql, data, page_size=1000)
        conn.commit()
        logger.info(f"Inserted {len(data)} records")
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"Insert failed: {e}")


# ============================================================================
# DATA FETCHING
# ============================================================================


def get_sp500_tickers() -> List[str]:
    """Fetch S&P 500 constituent tickers from yfinance."""
    try:
        # Try alternative source: use yfinance's built-in sp500 tickers
        import yfinance as yf
        tickers = yf.utils.get_tickers_sp500()
        if tickers:
            logger.info(f"Fetched {len(tickers)} S&P 500 tickers from yfinance")
            return tickers
    except Exception as e:
        logger.warning(f"Failed to fetch from yfinance: {e}")
    
    # Fallback: Use a smaller curated list of major S&P 500 stocks for demo
    fallback_tickers = [
        'AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMZN', 'META', 'GOOG', 'GOOGL', 
        'BERKB', 'JPM', 'JNJ', 'V', 'WMT', 'XOM', 'PG', 'MA', 'HD', 'KO',
        'MCD', 'PEP', 'PFE', 'ABBV', 'LLY', 'AVGO', 'TXN', 'ASML', 'AMD',
        'COST', 'CMCSA', 'NKE', 'ADBE', 'BA', 'IBM', 'INTC', 'VZ', 'T',
        'GS', 'BLK', 'SCHW', 'AXP', 'MMM', 'MRK', 'VRTX', 'CAT', 'GE'
    ]
    logger.warning(f"Using fallback list of {len(fallback_tickers)} major tickers")
    return fallback_tickers


def fetch_ticker_data(ticker: str) -> List[Tuple]:
    """Fetch hourly data for a single ticker. Returns list of tuples for insertion."""
    try:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=LOOKBACK_DAYS)

        df = yf.download(
            ticker,
            start=start_date,
            end=end_date,
            interval="1h",
            progress=False,
            threads=False,
        )

        if df.empty:
            logger.warning(f"{ticker}: No data returned")
            return []

        records = []
        for idx, row in df.iterrows():
            records.append(
                (
                    ticker,
                    idx,  # timestamp (index for hourly data)
                    float(row["Open"]),
                    float(row["High"]),
                    float(row["Low"]),
                    float(row["Close"]),
                    int(row["Volume"]),
                )
            )

        logger.info(f"{ticker}: Fetched {len(records)} hourly candles")
        return records

    except Exception as e:
        logger.error(f"{ticker}: Fetch failed: {e}")
        return []


def fetch_all_tickers(tickers: List[str]) -> List[Tuple]:
    """Parallel fetch for all tickers."""
    all_records = []
    completed = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(fetch_ticker_data, ticker): ticker for ticker in tickers
        }

        for future in as_completed(futures):
            ticker = futures[future]
            try:
                records = future.result()
                all_records.extend(records)
                completed += 1
                if completed % 25 == 0:
                    logger.info(f"Progress: {completed}/{len(tickers)} tickers")
            except Exception as e:
                logger.error(f"Task failed for {ticker}: {e}")

    logger.info(f"Total records fetched: {len(all_records)}")
    return all_records


# ============================================================================
# MAIN
# ============================================================================


def main():
    logger.info("=== S&P 500 Hourly Data Pipeline ===")
    logger.info(f"Lookback period: {LOOKBACK_DAYS} days")

    # Initialize DB
    init_db()

    # Get tickers
    tickers = get_sp500_tickers()
    if not tickers:
        logger.error("No tickers fetched. Exiting.")
        sys.exit(1)

    # Fetch and insert
    logger.info(f"Fetching hourly data for {len(tickers)} tickers...")
    records = fetch_all_tickers(tickers)

    logger.info(f"Inserting {len(records)} records into database...")
    insert_prices(records)

    logger.info("=== Pipeline Complete ===")


if __name__ == "__main__":
    main()
