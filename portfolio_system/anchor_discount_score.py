#!/usr/bin/env python3
"""
ANCHOR Strategy - Discount Assessment Module
Identifies temporary weakness in quality names.
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import numpy as np
import math

DB_CONFIG = {
    "host": "localhost",
    "database": "stock_data",
    "user": "postgres",
    "password": "stock_password",
    "port": 5432,
}

class DiscountScorer:
    """Assess discount/undervaluation of stocks"""
    
    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
    
    def close(self):
        if self.conn:
            self.cursor.close()
            self.conn.close()
    
    def get_ohlcv_history(self, ticker, days=252):
        """Fetch price history"""
        query = """
            SELECT timestamp, close, volume 
            FROM stock_prices 
            WHERE ticker = %s 
            ORDER BY timestamp DESC 
            LIMIT %s
        """
        self.cursor.execute(query, (ticker, days + 20))
        rows = list(reversed(self.cursor.fetchall()))
        return rows
    
    def rsi(self, prices, period=14):
        """Calculate RSI"""
        if len(prices) < period + 1:
            return 50.0
        deltas = [prices[i+1] - prices[i] for i in range(len(prices)-1)]
        seed = deltas[:period]
        up = sum(d for d in seed if d > 0) / period if sum(1 for d in seed if d > 0) > 0 else 0
        down = abs(sum(d for d in seed if d < 0) / period) if sum(1 for d in seed if d < 0) > 0 else 0
        rs = up / down if down > 0 else 0
        rsi_val = 100 - (100 / (1 + rs)) if rs >= 0 else 0
        return rsi_val
    
    def score_pullback(self, prices):
        """2A: Pullback from 52-week high"""
        if not prices or len(prices) < 252:
            return 0.0
        
        high_52w = max(prices[-252:])
        current = prices[-1]
        pullback = (current - high_52w) / high_52w if high_52w > 0 else 0
        
        # Scoring: target zone -10% to -30%
        if -0.30 <= pullback <= -0.20:
            return 100.0
        elif -0.20 < pullback <= -0.10:
            return 70.0
        elif -0.40 < pullback <= -0.30:
            return 40.0
        elif pullback > -0.10:
            return 20.0  # Too little pullback
        else:
            return 0.0  # Too much (fallen knife)
    
    def score_divergence(self, prices):
        """2A: Momentum divergence (long-term winner with short-term weakness)"""
        if len(prices) < 252:
            return 50.0
        
        momentum_21 = (prices[-1] - prices[-21]) / prices[-21] if len(prices) >= 21 else 0
        momentum_126 = (prices[-1] - prices[-126]) / prices[-126] if len(prices) >= 126 else 0
        momentum_252 = (prices[-1] - prices[-252]) / prices[-252] if len(prices) >= 252 else 0
        
        divergence = momentum_252 - momentum_21  # Long-term outperformance vs short-term
        
        # High positive divergence = good (long-term strength, short-term weakness)
        if momentum_252 > 0:
            # Normalize divergence to 0-100 scale
            div_score = 50 + (divergence * 50)
            return min(100, max(0, div_score))
        else:
            return 0.0  # Not a long-term winner
    
    def score_mean_reversion(self, prices):
        """2A: Mean reversion signals"""
        if len(prices) < 60:
            return 0.0
        
        rsi_14 = self.rsi(prices, 14)
        sma_50 = np.mean(prices[-50:])
        distance_50d = (prices[-1] - sma_50) / sma_50 if sma_50 > 0 else 0
        
        # Bollinger Bands (20, 2 std)
        sma_20 = np.mean(prices[-20:])
        std_20 = np.std(prices[-20:])
        lower_band = sma_20 - 2 * std_20
        upper_band = sma_20 + 2 * std_20
        bb_position = (prices[-1] - lower_band) / (upper_band - lower_band) if upper_band > lower_band else 0.5
        
        # Z-score
        mean_60 = np.mean(prices[-60:])
        std_60 = np.std(prices[-60:])
        z_score = (prices[-1] - mean_60) / std_60 if std_60 > 0 else 0
        
        # Combine signals: lower RSI, lower BB position, further below 50d = more oversold = higher score
        rsi_component = (100 - rsi_14) / 2 if rsi_14 < 50 else 0  # Cap at 50
        bb_component = (1 - bb_position) * 100
        dist_component = max(0, distance_50d * -100)  # Negative distance = lower score
        z_component = max(0, z_score * -25)  # Negative z = lower price
        
        reversion_score = (0.25 * rsi_component + 0.25 * bb_component + 
                          0.25 * dist_component + 0.25 * z_component)
        
        return min(100, max(0, reversion_score))
    
    def score_support(self, prices):
        """2A: Support level proximity"""
        if len(prices) < 252:
            return 30.0
        
        sma_200 = np.mean(prices[-200:])
        high_52w = max(prices[-252:])
        low_52w = min(prices[-252:])
        current = prices[-1]
        
        dist_200d = abs(current - sma_200) / sma_200 if sma_200 > 0 else 0
        dist_52w_low = (current - low_52w) / low_52w if low_52w > 0 else 0
        
        # Ideal: near 200d support but well above 52w low
        if dist_200d <= 0.05 and dist_52w_low > 0.15:
            return 100.0
        elif dist_200d <= 0.10 and dist_52w_low > 0.10:
            return 60.0
        else:
            return 30.0
    
    def score_discount(self, ticker):
        """Combined price-based discount score"""
        try:
            prices = self.get_ohlcv_history(ticker, 252)
            if len(prices) < 100:
                return None
            
            prices_only = [row['close'] for row in prices]
            
            # Component scores
            pullback = self.score_pullback(prices_only)
            divergence = self.score_divergence(prices_only)
            reversion = self.score_mean_reversion(prices_only)
            support = self.score_support(prices_only)
            
            # Weighted combination (no fundamental valuation data)
            discount_score = (
                0.30 * pullback +
                0.25 * divergence +
                0.25 * reversion +
                0.20 * support
            )
            
            return {
                'discount_score': discount_score,
                'pullback': pullback,
                'divergence': divergence,
                'reversion': reversion,
                'support': support,
                'rsi_14': self.rsi(prices_only, 14),
                'pullback_pct': ((prices_only[-1] - max(prices_only[-252:])) / max(prices_only[-252:]) * 100),
            }
        except Exception as e:
            print(f"Error scoring discount for {ticker}: {e}")
            return None

if __name__ == '__main__':
    scorer = DiscountScorer()
    result = scorer.score_discount('AAPL')
    if result:
        print(f"AAPL Discount Score: {result['discount_score']:.1f}")
        print(f"  Pullback: {result['pullback']:.1f}")
        print(f"  Divergence: {result['divergence']:.1f}")
        print(f"  Reversion: {result['reversion']:.1f}")
        print(f"  Support: {result['support']:.1f}")
        print(f"  RSI 14: {result['rsi_14']:.1f}")
    scorer.close()
