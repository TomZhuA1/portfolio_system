# S&P 500 Hourly Stock Data Pipeline

Fetches hourly OHLCV data for all S&P 500 constituents for the past 7 days and stores in PostgreSQL.

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up PostgreSQL

```bash
# Create database
psql -U postgres -f setup_db.sql

# Or manually:
psql -U postgres
CREATE DATABASE stock_data;
\c stock_data
-- Run the CREATE TABLE statements from setup_db.sql
```

### 3. Configure Connection

Edit `sp500_hourly_pipeline.py` line ~23 (DB_CONFIG) with your PostgreSQL credentials:

```python
DB_CONFIG = {
    "host": "localhost",
    "database": "stock_data",
    "user": "postgres",
    "password": "your_password",
    "port": 5432,
}
```

### 4. Run the Pipeline

```bash
python sp500_hourly_pipeline.py
```

**First run:** ~5–10 mins (500 stocks × 7 days × 24 hours ≈ 84k records)
**Subsequent runs:** Idempotent (upsert logic prevents duplicates)

## Usage

### Query Examples

```sql
-- Latest close for AAPL
SELECT timestamp, close FROM stock_prices 
WHERE ticker = 'AAPL' 
ORDER BY timestamp DESC LIMIT 1;

-- All data for a ticker
SELECT * FROM stock_prices 
WHERE ticker = 'MSFT'
ORDER BY timestamp DESC;

-- Tickers with most data points
SELECT ticker, COUNT(*) as records 
FROM stock_prices 
GROUP BY ticker 
ORDER BY records DESC;

-- Average hourly close by ticker
SELECT ticker, AVG(close) as avg_close 
FROM stock_prices 
GROUP BY ticker 
ORDER BY avg_close DESC;

-- Volatility (intraday high-low range)
SELECT ticker, timestamp, (high - low) as intraday_range 
FROM stock_prices 
WHERE date(timestamp) = CURRENT_DATE 
ORDER BY intraday_range DESC;
```

## Schema

```
Table: stock_prices
├── id (SERIAL PRIMARY KEY)
├── ticker (VARCHAR(10)) - stock symbol
├── timestamp (TIMESTAMP) - hour of the candle
├── open (FLOAT)
├── high (FLOAT)
├── low (FLOAT)
├── close (FLOAT)
├── volume (BIGINT)
├── created_at (TIMESTAMP) - insertion time
└── UNIQUE(ticker, timestamp) - prevents duplicates
```

## Notes

- **Idempotent:** Re-running the script upserts without duplicates
- **Rate limiting:** Uses threading with 8 workers; yfinance is lenient
- **Data freshness:** Pulls past 7 days on each run; modify `LOOKBACK_DAYS` as needed
- **Error handling:** Skips failed tickers and logs warnings

## Future Enhancements

- [ ] Scheduled runs (cron / APScheduler)
- [ ] Backfill historical data (months/years)
- [ ] Add technical indicators (SMA, RSI, etc.)
- [ ] Real-time streaming via WebSocket
- [ ] Data validation + quality checks
- [ ] Partitioning by date for large datasets
