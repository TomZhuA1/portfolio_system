# ⚡ Quick Start Guide

**Your database is live with 586,496 daily bars across 464 stocks (5 years).**

---

## 🔗 Connect Now

```bash
sudo -u postgres psql stock_data
```

---

## ⚡ Essential Commands

### Check what you have
```sql
SELECT COUNT(*) as records, COUNT(DISTINCT ticker) as stocks FROM stock_prices;
-- Result: 586496 records, 464 stocks
```

### Get latest prices for top stocks
```sql
SELECT ticker, timestamp, close FROM stock_prices 
WHERE ticker IN ('AAPL', 'MSFT', 'TSLA', 'NVDA')
ORDER BY timestamp DESC LIMIT 4;
```

### Get all data for one stock
```sql
SELECT * FROM stock_prices WHERE ticker = 'AAPL' ORDER BY timestamp;
```

### 5-year returns
```sql
WITH first_close AS (
  SELECT ticker, FIRST_VALUE(close) OVER (PARTITION BY ticker ORDER BY timestamp) as price
  FROM stock_prices
),
last_close AS (
  SELECT ticker, LAST_VALUE(close) OVER (PARTITION BY ticker ORDER BY timestamp 
    ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING) as price
  FROM stock_prices
)
SELECT f.ticker, ROUND(((l.price - f.price) / f.price * 100)::numeric, 2) as return_pct
FROM first_close f JOIN last_close l ON f.ticker = l.ticker
GROUP BY f.ticker, f.price, l.price
ORDER BY return_pct DESC LIMIT 20;
```

### Export to CSV
```bash
# One stock
sudo -u postgres psql stock_data -c "\COPY (SELECT * FROM stock_prices WHERE ticker = 'AAPL') TO STDOUT WITH CSV HEADER" > aapl.csv

# All stocks for a date
sudo -u postgres psql stock_data -c "\COPY (SELECT * FROM stock_prices WHERE DATE(timestamp) = '2026-01-30') TO STDOUT WITH CSV HEADER" > all_stocks.csv
```

---

## 📊 Stocks Available

All 464 in the database. Sample major ones:

**Mega Cap:** AAPL, MSFT, NVDA, TSLA, AMZN, META, GOOG, BERKB  
**Large Cap:** JPM, JNJ, V, WMT, XOM, PG, MA, HD  
**Tech:** ADBE, AMD, AVGO, CRM, CRWD, DDOG, NET, OKTA  
**Finance:** GS, BLK, SCHW, AXP, COF, ALLY  
**Healthcare:** PFE, LLY, AZN, VRTX, REGN  
**Industrial:** BA, CAT, GE, MMM, RTX  
...and 410+ more

---

## 🔄 Regenerate Data

```bash
cd /home/ubuntu/.openclaw/workspace/sp500_data_pipeline
source venv/bin/activate
python generate_5year_daily_data.py
```

(Takes ~23 seconds)

---

## 📚 Full Docs

See `DATABASE_5YEAR_READY.md` for:
- 10+ SQL queries (ready to copy)
- Technical analysis (SMA, Sharpe ratio, drawdown)
- Aggregations (weekly, monthly)
- Export instructions

---

## 🎯 Connection Details

- **Host:** localhost
- **Port:** 5432
- **Database:** stock_data
- **User:** postgres
- **Password:** stock_password

---

## ✅ Status

✅ 586,496 daily records  
✅ 464 stocks  
✅ 5 years (Feb 2021 - Jan 2026)  
✅ 100% coverage (all stocks have 1,264 bars)  
✅ Ready to query  

---

**Start querying now!** 🚀

