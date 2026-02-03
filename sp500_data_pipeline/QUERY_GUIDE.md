# S&P 500 Stock Price Database - Query Guide

**Status:** ✅ Ready to query | **Records:** 2,730 hourly candles | **Tickers:** 78 stocks

---

## Quick Start

```bash
sudo -u postgres psql stock_data
```

Then run any query below.

---

## 🔍 ESSENTIAL QUERIES

### 1. Get Latest Price for a Stock
```sql
SELECT ticker, timestamp, close as latest_price 
FROM stock_prices 
WHERE ticker = 'AAPL'
ORDER BY timestamp DESC LIMIT 1;
```
**Result:** Latest AAPL close + timestamp

---

### 2. Daily Summary (OHLCV)
```sql
SELECT ticker, DATE(timestamp) as date,
  ROUND(FIRST_VALUE(open) OVER (PARTITION BY ticker ORDER BY timestamp)::numeric, 2) as open,
  ROUND(MAX(high)::numeric, 2) as high,
  ROUND(MIN(low)::numeric, 2) as low,
  ROUND(LAST_VALUE(close) OVER (PARTITION BY ticker ORDER BY timestamp 
    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING)::numeric, 2) as close,
  SUM(volume) as volume
FROM stock_prices
WHERE DATE(timestamp) = CURRENT_DATE - INTERVAL '1 day'
GROUP BY ticker, DATE(timestamp)
ORDER BY ticker;
```

---

### 3. Top Gainers (Last Trading Day)
```sql
WITH daily AS (
  SELECT ticker, 
    FIRST_VALUE(open) OVER (PARTITION BY ticker ORDER BY timestamp) as day_open,
    LAST_VALUE(close) OVER (PARTITION BY ticker ORDER BY timestamp 
      ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as day_close
  FROM stock_prices
  WHERE DATE(timestamp) = '2026-01-30'
)
SELECT ticker, 
  ROUND(day_open::numeric, 2) as open,
  ROUND(day_close::numeric, 2) as close,
  ROUND(((day_close - day_open) / day_open * 100)::numeric, 2) as pct_gain
FROM daily
GROUP BY ticker, day_open, day_close
ORDER BY pct_gain DESC LIMIT 20;
```

---

### 4. Top Losers (Last Trading Day)
```sql
WITH daily AS (
  SELECT ticker, 
    FIRST_VALUE(open) OVER (PARTITION BY ticker ORDER BY timestamp) as day_open,
    LAST_VALUE(close) OVER (PARTITION BY ticker ORDER BY timestamp 
      ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as day_close
  FROM stock_prices
  WHERE DATE(timestamp) = '2026-01-30'
)
SELECT ticker, 
  ROUND(day_open::numeric, 2) as open,
  ROUND(day_close::numeric, 2) as close,
  ROUND(((day_close - day_open) / day_open * 100)::numeric, 2) as pct_loss
FROM daily
GROUP BY ticker, day_open, day_close
ORDER BY pct_loss ASC LIMIT 20;
```

---

### 5. Price Statistics by Ticker
```sql
SELECT ticker, 
  COUNT(*) as hourly_candles,
  ROUND(AVG(close)::numeric, 2) as avg_price,
  ROUND(MIN(low)::numeric, 2) as min_price,
  ROUND(MAX(high)::numeric, 2) as max_price,
  ROUND((MAX(high) - MIN(low))::numeric, 2) as price_range,
  ROUND(((MAX(high) - MIN(low)) / AVG(close) * 100)::numeric, 2) as volatility_pct,
  ROUND(SUM(volume)::numeric) as total_volume
FROM stock_prices
GROUP BY ticker
ORDER BY volatility_pct DESC
LIMIT 20;
```

---

### 6. Highest Volume Hours
```sql
SELECT ticker, timestamp, volume, close
FROM stock_prices
WHERE DATE(timestamp) = '2026-01-30'
ORDER BY volume DESC
LIMIT 10;
```

---

### 7. Intraday Volatility (High-Low Range)
```sql
SELECT ticker, timestamp,
  ROUND((high - low)::numeric, 2) as intraday_range,
  ROUND(((high - low) / open * 100)::numeric, 2) as intraday_volatility_pct
FROM stock_prices
WHERE DATE(timestamp) = '2026-01-30'
ORDER BY intraday_volatility_pct DESC
LIMIT 20;
```

---

### 8. Hour-by-Hour Trend (Single Stock)
```sql
SELECT ticker, timestamp, 
  ROUND(open::numeric, 2) as open,
  ROUND(close::numeric, 2) as close,
  ROUND((close - open)::numeric, 2) as change,
  ROUND(((close - open) / open * 100)::numeric, 2) as pct_change,
  volume
FROM stock_prices
WHERE ticker = 'AAPL'
  AND DATE(timestamp) = '2026-01-30'
ORDER BY timestamp;
```

---

### 9. Compare Multiple Stocks
```sql
SELECT ticker,
  ROUND(MIN(low)::numeric, 2) as low,
  ROUND(MAX(close)::numeric, 2) as high,
  ROUND(AVG(close)::numeric, 2) as avg,
  ROUND(SUM(volume)::numeric) as total_vol
FROM stock_prices
WHERE ticker IN ('AAPL', 'MSFT', 'TSLA', 'AMZN', 'GOOG')
  AND DATE(timestamp) = '2026-01-30'
GROUP BY ticker
ORDER BY ticker;
```

---

### 10. Database Info
```sql
-- Total records and coverage
SELECT COUNT(*) as total_records, 
  COUNT(DISTINCT ticker) as num_tickers,
  MIN(timestamp) as earliest,
  MAX(timestamp) as latest
FROM stock_prices;

-- Records per ticker
SELECT ticker, COUNT(*) as candles
FROM stock_prices
GROUP BY ticker
ORDER BY candles DESC;
```

---

## 📊 ANALYSIS QUERIES

### Momentum (Last 5 hours)
```sql
WITH recent AS (
  SELECT ticker, close,
    LAG(close, 4) OVER (PARTITION BY ticker ORDER BY timestamp) as close_4h_ago
  FROM stock_prices
  WHERE timestamp > NOW() - INTERVAL '5 hours'
)
SELECT ticker,
  ROUND(((close - close_4h_ago) / close_4h_ago * 100)::numeric, 2) as momentum_pct
FROM recent
WHERE close_4h_ago IS NOT NULL
ORDER BY momentum_pct DESC;
```

### Moving Average (20-hour SMA)
```sql
SELECT ticker, timestamp, close,
  ROUND(AVG(close) OVER (
    PARTITION BY ticker 
    ORDER BY timestamp 
    ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
  )::numeric, 2) as sma_20
FROM stock_prices
ORDER BY ticker, timestamp DESC;
```

### Volume Trend
```sql
SELECT ticker, timestamp, volume,
  ROUND(AVG(volume) OVER (
    PARTITION BY ticker 
    ORDER BY timestamp 
    ROWS BETWEEN 9 PRECEDING AND CURRENT ROW
  )::numeric) as volume_10h_avg
FROM stock_prices
ORDER BY ticker, timestamp DESC;
```

---

## 🛠️ MAINTENANCE

### Check Data Integrity
```sql
-- Records per day
SELECT DATE(timestamp) as date, COUNT(*) as records
FROM stock_prices
GROUP BY DATE(timestamp)
ORDER BY date DESC;

-- Gaps in data (should be zero if healthy)
SELECT ticker, COUNT(DISTINCT DATE(timestamp)) as trading_days
FROM stock_prices
GROUP BY ticker
HAVING COUNT(DISTINCT DATE(timestamp)) < 5;
```

### Export to CSV
```bash
sudo -u postgres psql stock_data -c "\COPY (
  SELECT ticker, timestamp, open, high, low, close, volume
  FROM stock_prices
  WHERE DATE(timestamp) = '2026-01-30'
  ORDER BY ticker, timestamp
) TO STDOUT WITH CSV HEADER" > sp500_2026-01-30.csv
```

---

## 💡 Tips

- **Replace dates:** Use actual dates in the data (2026-01-26 to 2026-01-30)
- **Change symbols:** Swap 'AAPL' with any ticker in the database
- **Batch queries:** Combine multiple selects with CTEs (WITH ... AS)
- **Performance:** Indexes on (ticker, timestamp) make lookups instant

---

## Data Dictionary

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| ticker | VARCHAR(10) | Stock symbol (e.g., 'AAPL') |
| timestamp | TIMESTAMP | Hour of the candle |
| open | FLOAT | Opening price |
| high | FLOAT | Intraday high |
| low | FLOAT | Intraday low |
| close | FLOAT | Closing price |
| volume | BIGINT | Trading volume |
| created_at | TIMESTAMP | Insertion time |

---

**Ready to query!** 🚀
