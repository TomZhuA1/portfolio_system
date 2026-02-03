#!/usr/bin/env python3
"""
Backtest the Phase 1 strategy on historical data.
Validates strategy performance before deploying daily.
"""

import psycopg2
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

DB_CONFIG = {
    "host": "localhost",
    "database": "stock_data",
    "user": "postgres",
    "password": "stock_password",
    "port": 5432,
}

def backtest_strategy(lookback_days=252):
    """
    Backtest the strategy: daily recommendations vs actual returns.
    
    Approach:
    1. For each day in past 252 days:
       - Calculate signals using data up to that day
       - Rank stocks and select top 50
       - Equal weight (2% each)
       - Measure return over next 5 days
    2. Track win rate, avg gain, max drawdown
    """
    
    conn = psycopg2.connect(**DB_CONFIG)
    query = """
        SELECT ticker, timestamp, close
        FROM stock_prices
        WHERE timestamp >= NOW() - INTERVAL '2 years'
        ORDER BY ticker, timestamp
    """
    df = pd.read_sql(query, conn)
    conn.close()
    
    # Get unique dates
    dates = sorted(df['timestamp'].unique())
    
    # Start backtest from 1 year ago (need history for signals)
    test_start_idx = len(dates) - lookback_days
    test_dates = dates[test_start_idx:]
    
    print(f"Backtesting from {test_dates[0].date()} to {test_dates[-1].date()}")
    print(f"Total trading days: {len(test_dates)}\n")
    
    # Track results
    daily_returns = []
    winning_days = 0
    losing_days = 0
    
    for i, test_date in enumerate(test_dates[:-5]):  # Need 5 days forward
        
        # Get data up to test_date
        hist_data = df[df['timestamp'] <= test_date]
        
        if len(hist_data) < 200:
            continue
        
        # Calculate signals (same as phase1)
        signals = []
        for ticker in hist_data['ticker'].unique():
            stock_data = hist_data[hist_data['ticker'] == ticker].sort_values('timestamp')
            
            if len(stock_data) < 200:
                continue
            
            current_price = stock_data['close'].iloc[-1]
            price_10d_ago = stock_data['close'].iloc[-10] if len(stock_data) >= 10 else stock_data['close'].iloc[0]
            
            momentum = ((current_price - price_10d_ago) / price_10d_ago) * 100
            
            sma_200 = stock_data['close'].iloc[-200:].mean()
            trend_score = 1.0 if current_price > sma_200 else 0.0
            
            returns = stock_data['close'].pct_change().dropna()
            volatility = returns.std() * np.sqrt(252)
            quality_score = 1.0 / (1.0 + volatility)
            
            composite_score = (momentum / 10 + trend_score + quality_score) / 3
            
            signals.append({
                'ticker': ticker,
                'price': current_price,
                'composite_score': composite_score,
            })
        
        if not signals:
            continue
        
        # Select top 50
        signals_df = pd.DataFrame(signals).sort_values('composite_score', ascending=False)
        top_50 = signals_df.head(50)
        
        # Calculate 5-day forward return (equal weight)
        future_prices = {}
        for ticker in top_50['ticker']:
            future_data = df[(df['ticker'] == ticker) & (df['timestamp'] > test_date) & (df['timestamp'] <= test_date + timedelta(days=5))]
            if len(future_data) > 0:
                future_price = future_data['close'].iloc[-1]
                current_price = top_50[top_50['ticker'] == ticker]['price'].values[0]
                future_prices[ticker] = (future_price - current_price) / current_price
        
        if not future_prices:
            continue
        
        # Portfolio return (equal weight)
        portfolio_return = np.mean(list(future_prices.values()))
        daily_returns.append(portfolio_return)
        
        if portfolio_return > 0:
            winning_days += 1
        else:
            losing_days += 1
        
        # Progress
        if i % 50 == 0:
            print(f"  Day {i}: {test_date.date()} | Return: {portfolio_return:+.2%}")
    
    # Calculate metrics
    daily_returns = np.array(daily_returns)
    
    print(f"\n" + "=" * 70)
    print("BACKTEST RESULTS")
    print("=" * 70)
    print(f"Total trading days tested: {len(daily_returns)}")
    print(f"Winning days: {winning_days} ({winning_days/len(daily_returns)*100:.1f}%)")
    print(f"Losing days: {losing_days} ({losing_days/len(daily_returns)*100:.1f}%)")
    print(f"\nAverage 5-day return: {daily_returns.mean():+.2%}")
    print(f"Std dev: {daily_returns.std():.2%}")
    print(f"Sharpe ratio (5d): {daily_returns.mean() / daily_returns.std() * np.sqrt(252/5) if daily_returns.std() > 0 else 0:.2f}")
    print(f"\nBest day: {daily_returns.max():+.2%}")
    print(f"Worst day: {daily_returns.min():+.2%}")
    print(f"Cumulative return: {(1 + daily_returns).prod() - 1:+.2%}")
    
    return {
        'daily_returns': daily_returns,
        'win_rate': winning_days / len(daily_returns),
        'avg_return': daily_returns.mean(),
        'sharpe': daily_returns.mean() / daily_returns.std() * np.sqrt(252/5),
        'cumulative': (1 + daily_returns).prod() - 1,
    }

if __name__ == "__main__":
    results = backtest_strategy(lookback_days=252)
