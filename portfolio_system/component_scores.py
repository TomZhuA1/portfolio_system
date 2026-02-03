#!/usr/bin/env python3
"""
Calculate 6 component scores for stock ranking:
1. Risk-Adjusted Momentum (21d, 63d, 126d, 252d Sharpe)
2. Trend Quality (MA alignment, trend strength, position in range, higher lows)
3. Volatility-Adjusted (vol-adjusted returns)
4. Volume Confirmation (volume trends, price-volume correlation)
5. Relative Strength (sector + market relative performance)
6. Oversold Score (RSI bounce opportunity)
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import numpy as np
from datetime import datetime, timedelta
import math

DB_CONFIG = {
    "host": "localhost",
    "database": "stock_data",
    "user": "postgres",
    "password": "stock_password",
    "port": 5432,
}

class ComponentScorer:
    """Calculate all 6 component scores for a single stock"""
    
    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
    
    def close(self):
        if self.conn:
            self.cursor.close()
            self.conn.close()
    
    def get_ohlcv(self, ticker, days=252):
        """Fetch last N days of OHLCV data"""
        query = """
            SELECT timestamp, open, high, low, close, volume 
            FROM stock_prices 
            WHERE ticker = %s 
            ORDER BY timestamp DESC 
            LIMIT %s
        """
        self.cursor.execute(query, (ticker, days + 20))  # Extra buffer for calculations
        rows = list(reversed(self.cursor.fetchall()))
        return rows
    
    def percentile_rank(self, value, population):
        """Calculate percentile rank of value within population (0-100)"""
        if not population or len(population) < 2:
            return 50.0
        sorted_pop = sorted(population)
        rank = sum(1 for x in sorted_pop if x < value) / len(sorted_pop)
        return rank * 100.0
    
    def rsi(self, prices, period=14):
        """Calculate RSI"""
        if len(prices) < period + 1:
            return 50.0
        deltas = [prices[i+1] - prices[i] for i in range(len(prices)-1)]
        seed = deltas[:period]
        up = sum(1 for d in seed if d > 0) * (sum(d for d in seed if d > 0) / period)
        down = sum(1 for d in seed if d < 0) * (abs(sum(d for d in seed if d < 0)) / period)
        rs = up / down if down > 0 else 0
        rsi_val = 100 - (100 / (1 + rs)) if rs >= 0 else 0
        return rsi_val
    
    def score_momentum(self, prices):
        """2A: Risk-Adjusted Momentum Score"""
        risk_free_daily = 0.05 / 252
        periods = [21, 63, 126, 252]
        weights = [0.35, 0.30, 0.20, 0.15]
        
        sharpe_scores = []
        for period in periods:
            if len(prices) < period:
                sharpe_scores.append(50.0)
                continue
            
            recent_prices = prices[-period:]
            returns = [(recent_prices[i+1] - recent_prices[i]) / recent_prices[i] 
                      for i in range(len(recent_prices)-1)]
            excess_return = np.mean(returns) - risk_free_daily if returns else 0
            vol = np.std(returns) if returns else 0.001
            sharpe = (excess_return / vol * math.sqrt(252)) if vol > 0 else 0
            sharpe_scores.append(sharpe)
        
        # Normalize to percentile (0-100)
        normalized = [max(0, min(100, 50 + s * 5)) for s in sharpe_scores]
        momentum_score = sum(w * s for w, s in zip(weights, normalized))
        return momentum_score
    
    def score_trend(self, prices):
        """2B: Trend Quality Score"""
        if len(prices) < 200:
            return 50.0
        
        # SMA calculations
        sma_20 = np.mean(prices[-20:])
        sma_50 = np.mean(prices[-50:])
        sma_200 = np.mean(prices[-200:])
        current_price = prices[-1]
        
        # Trend strength
        trend_strength = (current_price - sma_200) / sma_200 if sma_200 > 0 else 0
        trend_strength_pctl = 50 + (trend_strength * 100)  # Normalize
        
        # MA alignment
        if sma_20 > sma_50 > sma_200:
            ma_alignment = 1.0
        elif sum([sma_20 > sma_50, sma_50 > sma_200, sma_20 > sma_200]) >= 2:
            ma_alignment = 0.5
        else:
            ma_alignment = 0.0
        
        # Price vs 52-week high/low
        high_52w = max(prices[-252:]) if len(prices) >= 252 else max(prices)
        low_52w = min(prices[-252:]) if len(prices) >= 252 else min(prices)
        price_vs_range = (current_price - low_52w) / (high_52w - low_52w) if high_52w > low_52w else 0.5
        
        # Higher lows
        rolling_mins = [min(prices[max(0, i-20):i+1]) for i in range(len(prices)-60, len(prices))]
        higher_lows = sum(1 for i in range(1, len(rolling_mins)) if rolling_mins[i] > rolling_mins[i-1])
        higher_lows_score = (higher_lows / 3) * 33  # Scale 0-3 to 0-99
        
        trend_score = (0.30 * trend_strength_pctl + 
                      0.25 * (ma_alignment * 100) + 
                      0.25 * (price_vs_range * 100) + 
                      0.20 * higher_lows_score)
        
        return min(100, max(0, trend_score))
    
    def score_volatility(self, prices):
        """2C: Volatility-Adjusted Score"""
        if len(prices) < 60:
            return 50.0
        
        recent_60 = prices[-60:]
        returns_60 = [(recent_60[i+1] - recent_60[i]) / recent_60[i] for i in range(len(recent_60)-1)]
        vol_60d = np.std(returns_60) * math.sqrt(252) * 100  # Annualized %
        
        # Return per unit of volatility
        return_63d = (prices[-1] - prices[-63]) / prices[-63] if len(prices) >= 63 else 0
        return_per_vol = (return_63d / (vol_60d / 100)) if vol_60d > 0 else 0
        
        # Vol stability (penalize erratic vol)
        rolling_vols = []
        for i in range(len(prices) - 60, len(prices) - 20):
            segment = prices[i:i+20]
            seg_returns = [(segment[j+1] - segment[j]) / segment[j] for j in range(len(segment)-1)]
            rolling_vols.append(np.std(seg_returns) * math.sqrt(252) * 100)
        vol_stability = np.std(rolling_vols) if rolling_vols else 0
        
        # Inverse percentiles (lower vol is better)
        vol_score = (0.5 * (100 - vol_60d) +  # Inverse: lower vol = higher score
                    0.3 * max(0, min(100, return_per_vol * 20)) +
                    0.2 * max(0, 100 - vol_stability))
        
        return min(100, max(0, vol_score))
    
    def score_volume(self, ohlcv):
        """2D: Volume Confirmation Score"""
        if len(ohlcv) < 60:
            return 50.0
        
        volumes_60 = [row['volume'] for row in ohlcv[-60:]]
        volumes_20 = [row['volume'] for row in ohlcv[-20:]]
        volumes_40 = [row['volume'] for row in ohlcv[-40:]]
        
        # Volume ratio (20d vs 60d)
        avg_vol_20 = np.mean(volumes_20)
        avg_vol_60 = np.mean(volumes_60)
        vol_ratio = (avg_vol_20 / avg_vol_60) if avg_vol_60 > 0 else 1.0
        
        # Up day volume ratio
        up_volumes = []
        down_volumes = []
        for i in range(len(ohlcv) - 40, len(ohlcv)):
            row = ohlcv[i]
            if row['close'] > row['open']:
                up_volumes.append(row['volume'])
            else:
                down_volumes.append(row['volume'])
        
        up_day_vol_ratio = (np.mean(up_volumes) / np.mean(down_volumes) 
                           if down_volumes and np.mean(down_volumes) > 0 else 1.0)
        
        # Price-volume correlation
        prices = [row['close'] for row in ohlcv[-60:]]
        returns = [(prices[i+1] - prices[i]) / prices[i] for i in range(len(prices)-1)]
        volumes_norm = [v / np.mean(volumes_60) for v in volumes_60[:-1]]
        
        if len(returns) > 1 and len(volumes_norm) > 1:
            corr = np.corrcoef(returns, volumes_norm)[0, 1]
            price_vol_corr = (corr + 1) * 50  # Normalize to 0-100
        else:
            price_vol_corr = 50.0
        
        volume_score = (0.40 * (vol_ratio * 50) +
                       0.35 * (up_day_vol_ratio * 50) +
                       0.25 * price_vol_corr)
        
        return min(100, max(0, volume_score))
    
    def score_relative_strength(self, ticker, prices, sector):
        """2F: Relative Strength (simplified: vs market only)"""
        if len(prices) < 63:
            return 50.0
        
        stock_return_63 = (prices[-1] - prices[-63]) / prices[-63] if prices[-63] > 0 else 0
        
        # Get SPY (market) 63d return
        self.cursor.execute("""
            SELECT close FROM stock_prices 
            WHERE ticker = 'SPY' 
            ORDER BY timestamp DESC LIMIT 63
        """)
        spy_data = list(reversed(self.cursor.fetchall()))
        if len(spy_data) >= 63:
            spy_return = (spy_data[-1]['close'] - spy_data[0]['close']) / spy_data[0]['close']
            market_relative = stock_return_63 - spy_return
        else:
            market_relative = 0
        
        # Normalize to 0-100
        relative_score = 50 + (market_relative * 100)
        return min(100, max(0, relative_score))
    
    def score_oversold(self, prices):
        """2E: Oversold Score (bounce opportunity)"""
        if len(prices) < 50:
            return 0.0
        
        rsi_14 = self.rsi(prices, 14)
        sma_50 = np.mean(prices[-50:])
        distance_from_50d = (prices[-1] - sma_50) / sma_50 if sma_50 > 0 else 0
        
        high_63 = max(prices[-63:]) if len(prices) >= 63 else max(prices)
        drawdown = (prices[-1] - high_63) / high_63 if high_63 > 0 else 0
        
        if rsi_14 < 30 and distance_from_50d < -0.10 and drawdown < -0.15:
            return 100.0
        elif rsi_14 < 40 and distance_from_50d < -0.05:
            return 50.0
        else:
            return 0.0

if __name__ == '__main__':
    scorer = ComponentScorer()
    # Test with AAPL
    ohlcv = scorer.get_ohlcv('AAPL', 252)
    prices = [row['close'] for row in ohlcv]
    
    print(f"AAPL Component Scores:")
    print(f"  Momentum: {scorer.score_momentum(prices):.1f}")
    print(f"  Trend: {scorer.score_trend(prices):.1f}")
    print(f"  Volatility: {scorer.score_volatility(prices):.1f}")
    print(f"  Volume: {scorer.score_volume(ohlcv):.1f}")
    print(f"  Relative Strength: {scorer.score_relative_strength('AAPL', prices, 'Information Technology'):.1f}")
    print(f"  Oversold: {scorer.score_oversold(prices):.1f}")
    
    scorer.close()
