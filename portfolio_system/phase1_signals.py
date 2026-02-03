#!/usr/bin/env python3
"""
PHASE 1: Simple Rules-Based Stock Scoring
Ranks all 464 stocks by momentum, trend, and quality.
Output: Top 50 for portfolio.
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

def get_stock_data():
    """Fetch latest price data for all 464 stocks."""
    conn = psycopg2.connect(**DB_CONFIG)
    query = """
        SELECT ticker, timestamp, close, volume
        FROM stock_prices
        WHERE timestamp >= NOW() - INTERVAL '1 year'
        ORDER BY ticker, timestamp
    """
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def calculate_signals(df):
    """
    Calculate 3 simple signals for each stock:
    1. MOMENTUM: 10-day return (recent price action)
    2. TREND: Is price above 200-day SMA? (long-term trend)
    3. QUALITY: Volatility (lower = more stable/quality)
    """
    
    signals = []
    
    for ticker in df['ticker'].unique():
        stock_data = df[df['ticker'] == ticker].copy().sort_values('timestamp')
        
        if len(stock_data) < 200:
            continue  # Skip if not enough history
        
        current_price = stock_data['close'].iloc[-1]
        price_10d_ago = stock_data['close'].iloc[-10] if len(stock_data) >= 10 else stock_data['close'].iloc[0]
        
        # Signal 1: Momentum (10-day return)
        momentum = ((current_price - price_10d_ago) / price_10d_ago) * 100
        
        # Signal 2: Trend (price vs 200-day SMA)
        sma_200 = stock_data['close'].iloc[-200:].mean()
        trend_score = 1.0 if current_price > sma_200 else 0.0
        
        # Signal 3: Quality (inverse of volatility - lower vol = higher quality)
        returns = stock_data['close'].pct_change().dropna()
        volatility = returns.std() * np.sqrt(252)  # Annualized
        quality_score = 1.0 / (1.0 + volatility)  # Normalize to 0-1
        
        # Composite score (simple average of 3 signals)
        composite_score = (momentum / 10 + trend_score + quality_score) / 3
        
        signals.append({
            'ticker': ticker,
            'current_price': current_price,
            'momentum_pct': round(momentum, 2),
            'trend_score': trend_score,
            'volatility': round(volatility, 2),
            'quality_score': round(quality_score, 3),
            'composite_score': round(composite_score, 3),
        })
    
    return pd.DataFrame(signals).sort_values('composite_score', ascending=False).reset_index(drop=True)

def generate_recommendation(scores_df):
    """
    Generate portfolio recommendation:
    - Top 50 stocks for buying
    - Equal weight 2% each
    """
    
    top_50 = scores_df.head(50).copy()
    top_50['recommended_weight_pct'] = 2.0
    
    bottom_50 = scores_df.tail(50).copy()
    
    return {
        'timestamp': datetime.now(),
        'top_50': top_50,
        'bottom_50': bottom_50,
        'all_scores': scores_df,
        'stats': {
            'total_stocks': len(scores_df),
            'avg_momentum_top50': top_50['momentum_pct'].mean(),
            'avg_volatility_top50': top_50['volatility'].mean(),
        }
    }

def main():
    print("=" * 80)
    print("PHASE 1: SIMPLE RULES-BASED RECOMMENDATION")
    print("=" * 80)
    
    print("\nFetching price data for all 464 stocks...")
    df = get_stock_data()
    
    print(f"Calculating signals...")
    scores = calculate_signals(df)
    
    print(f"Generating recommendation...")
    recommendation = generate_recommendation(scores)
    
    # Display results
    print(f"\n✅ RECOMMENDATION GENERATED - {recommendation['timestamp'].strftime('%Y-%m-%d %H:%M')}")
    print(f"\nTOP 20 STOCKS TO BUY:")
    print(recommendation['top_50'][['ticker', 'current_price', 'momentum_pct', 'volatility', 'composite_score']].head(20).to_string(index=False))
    
    print(f"\nBOTTOM 20 STOCKS TO AVOID:")
    print(recommendation['bottom_50'][['ticker', 'current_price', 'momentum_pct', 'volatility', 'composite_score']].head(20).to_string(index=False))
    
    print(f"\n📊 PORTFOLIO STATS:")
    print(f"  Avg Momentum (Top 50): {recommendation['stats']['avg_momentum_top50']:.2f}%")
    print(f"  Avg Volatility (Top 50): {recommendation['stats']['avg_volatility_top50']:.2f} (annualized)")
    
    return recommendation

if __name__ == "__main__":
    main()
