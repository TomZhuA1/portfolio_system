-- S&P 500 Hourly Stock Data Database Setup
-- Run as: psql -U postgres -f setup_db.sql

-- Create database
CREATE DATABASE stock_data;

-- Connect to the database
\c stock_data

-- Create schema
CREATE TABLE stock_prices (
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

-- Indexes for common queries
CREATE INDEX idx_ticker_timestamp ON stock_prices(ticker, timestamp DESC);
CREATE INDEX idx_ticker ON stock_prices(ticker);
CREATE INDEX idx_timestamp ON stock_prices(timestamp DESC);

-- Summary table (optional, for quick stats)
CREATE TABLE ticker_stats (
    ticker VARCHAR(10) PRIMARY KEY,
    last_updated TIMESTAMP,
    record_count INT,
    start_date TIMESTAMP,
    end_date TIMESTAMP
);

-- Grant permissions (if using a dedicated user)
-- CREATE USER stock_user WITH PASSWORD 'your_password';
-- GRANT ALL ON DATABASE stock_data TO stock_user;
-- GRANT ALL ON ALL TABLES IN SCHEMA public TO stock_user;
