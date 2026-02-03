-- S&P 500 Hourly Stock Data - Useful Queries

-- ============================================================================
-- BASIC LOOKUPS
-- ============================================================================

-- Latest close for a specific ticker
SELECT timestamp, close FROM stock_prices 
WHERE ticker = 'AAPL' 
ORDER BY timestamp DESC LIMIT 1;

-- All data for a ticker (last 24 hours)
SELECT * FROM stock_prices 
WHERE ticker = 'MSFT' 
  AND timestamp > NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;

-- All tickers in database
SELECT DISTINCT ticker FROM stock_prices ORDER BY ticker;

-- Count of tickers and total records
SELECT COUNT(DISTINCT ticker) as num_tickers, COUNT(*) as total_records 
FROM stock_prices;


-- ============================================================================
-- AGGREGATIONS & STATISTICS
-- ============================================================================

-- Tickers with most data points
SELECT ticker, COUNT(*) as record_count 
FROM stock_prices 
GROUP BY ticker 
ORDER BY record_count DESC 
LIMIT 20;

-- Average hourly close by ticker (all time)
SELECT ticker, AVG(close) as avg_close, MIN(close) as min_close, MAX(close) as max_close
FROM stock_prices 
GROUP BY ticker 
ORDER BY avg_close DESC;

-- Intraday volatility (high-low range) for latest day
SELECT ticker, timestamp, 
  (high - low) as intraday_range,
  ROUND((high - low) / open * 100, 2) as range_pct
FROM stock_prices 
WHERE date(timestamp) = CURRENT_DATE
ORDER BY intraday_range DESC;

-- Average volume by ticker
SELECT ticker, ROUND(AVG(volume)) as avg_volume 
FROM stock_prices 
GROUP BY ticker 
ORDER BY avg_volume DESC;


-- ============================================================================
-- PRICE MOVEMENTS
-- ============================================================================

-- Hourly price changes for a ticker
SELECT ticker, timestamp,
  close - LAG(close) OVER (ORDER BY timestamp) as price_change,
  ROUND((close - LAG(close) OVER (ORDER BY timestamp)) / 
    LAG(close) OVER (ORDER BY timestamp) * 100, 3) as price_change_pct
FROM stock_prices
WHERE ticker = 'AAPL'
ORDER BY timestamp DESC
LIMIT 24;

-- Daily high/low for all tickers (most recent day)
SELECT ticker,
  DATE(timestamp) as date,
  MAX(high) as day_high,
  MIN(low) as day_low,
  FIRST_VALUE(open) OVER (PARTITION BY ticker ORDER BY timestamp) as open,
  LAST_VALUE(close) OVER (PARTITION BY ticker ORDER BY timestamp 
    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as close
FROM stock_prices
WHERE DATE(timestamp) = CURRENT_DATE
GROUP BY ticker, DATE(timestamp)
ORDER BY ticker;

-- Top gainers (last 24 hours)
WITH latest AS (
  SELECT ticker, timestamp, close,
    ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY timestamp DESC) as rn
  FROM stock_prices
  WHERE timestamp > NOW() - INTERVAL '24 hours'
)
SELECT l1.ticker,
  ROUND((l1.close - l2.close) / l2.close * 100, 2) as pct_change
FROM latest l1
JOIN latest l2 ON l1.ticker = l2.ticker 
  AND l1.rn = 1 AND l2.rn = (SELECT COUNT(*) FROM latest WHERE ticker = l1.ticker)
ORDER BY pct_change DESC
LIMIT 20;

-- Top losers (last 24 hours)
WITH latest AS (
  SELECT ticker, timestamp, close,
    ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY timestamp DESC) as rn
  FROM stock_prices
  WHERE timestamp > NOW() - INTERVAL '24 hours'
)
SELECT l1.ticker,
  ROUND((l1.close - l2.close) / l2.close * 100, 2) as pct_change
FROM latest l1
JOIN latest l2 ON l1.ticker = l2.ticker 
  AND l1.rn = 1 AND l2.rn = (SELECT COUNT(*) FROM latest WHERE ticker = l1.ticker)
ORDER BY pct_change ASC
LIMIT 20;


-- ============================================================================
-- DATA QUALITY
-- ============================================================================

-- Missing tickers (if S&P 500 has 500+ stocks)
SELECT COUNT(DISTINCT ticker) as unique_tickers FROM stock_prices;

-- Data coverage by ticker (records per ticker)
SELECT ticker, COUNT(*) as record_count,
  MIN(timestamp) as first_record,
  MAX(timestamp) as latest_record,
  EXTRACT(HOUR FROM MAX(timestamp) - MIN(timestamp)) as hours_covered
FROM stock_prices
GROUP BY ticker
ORDER BY record_count DESC;

-- Check for gaps in hourly data (for a ticker)
WITH hours AS (
  SELECT ticker, timestamp,
    LAG(timestamp) OVER (PARTITION BY ticker ORDER BY timestamp) as prev_timestamp
  FROM stock_prices
  WHERE ticker = 'AAPL'
)
SELECT ticker, timestamp, prev_timestamp,
  EXTRACT(HOUR FROM timestamp - prev_timestamp) as gap_hours
FROM hours
WHERE EXTRACT(HOUR FROM timestamp - prev_timestamp) > 1
ORDER BY timestamp DESC;

-- Recent records (last 10 inserts)
SELECT * FROM stock_prices 
ORDER BY created_at DESC, timestamp DESC
LIMIT 10;


-- ============================================================================
-- MAINTENANCE
-- ============================================================================

-- Count records by date
SELECT DATE(timestamp) as date, COUNT(*) as record_count
FROM stock_prices
GROUP BY DATE(timestamp)
ORDER BY date DESC;

-- Total data size
SELECT 
  pg_size_pretty(pg_total_relation_size('stock_prices')) as table_size,
  COUNT(*) as total_records
FROM stock_prices;

-- Update ticker stats (if ticker_stats table exists)
TRUNCATE TABLE ticker_stats;

INSERT INTO ticker_stats (ticker, last_updated, record_count, start_date, end_date)
SELECT 
  ticker,
  NOW(),
  COUNT(*) as record_count,
  MIN(timestamp) as start_date,
  MAX(timestamp) as end_date
FROM stock_prices
GROUP BY ticker;

SELECT * FROM ticker_stats ORDER BY record_count DESC;
