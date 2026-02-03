#!/usr/bin/env python3
"""
Market Regime Detection using SPY/IWM volatility metrics.
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

class RegimeDetector:
    """Detect market regime (LOW_VOL, NORMAL, HIGH_VOL, CRISIS)"""
    
    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
    
    def close(self):
        if self.conn:
            self.cursor.close()
            self.conn.close()
    
    def get_returns(self, ticker, days=60):
        """Fetch last N days of close prices"""
        query = """
            SELECT timestamp, close 
            FROM stock_prices 
            WHERE ticker = %s 
            ORDER BY timestamp DESC 
            LIMIT %s
        """
        self.cursor.execute(query, (ticker, days + 1))
        rows = list(reversed(self.cursor.fetchall()))
        
        if len(rows) < 2:
            return None
        
        closes = [r['close'] for r in rows]
        returns = [(closes[i+1] - closes[i]) / closes[i] for i in range(len(closes)-1)]
        return returns
    
    def annualized_vol(self, returns):
        """Calculate annualized volatility from daily returns"""
        if not returns or len(returns) < 2:
            return 0.0
        daily_vol = np.std(returns)
        annualized = daily_vol * math.sqrt(252)
        return annualized * 100  # Return as percentage
    
    def detect_regime(self):
        """
        Detect market regime using SPY (S&P 500) volatility.
        Returns: regime_name, realized_vol_20d, realized_vol_60d, vol_ratio
        """
        # Get returns for SPY (20d and 60d)
        returns_60 = self.get_returns('SPY', 60)
        
        if not returns_60 or len(returns_60) < 20:
            # Default to NORMAL if insufficient data
            return 'NORMAL', 15.0, 15.0, 1.0
        
        returns_20 = returns_60[-20:]
        
        vol_20d = self.annualized_vol(returns_20)
        vol_60d = self.annualized_vol(returns_60)
        vol_ratio = vol_20d / vol_60d if vol_60d > 0 else 1.0
        
        # Classify regime
        if vol_20d > 35:
            regime = 'CRISIS'
        elif vol_ratio > 1.15 or vol_20d > 25:
            regime = 'HIGH_VOL'
        elif vol_ratio < 0.85 and vol_20d < 15:
            regime = 'LOW_VOL'
        else:
            regime = 'NORMAL'
        
        return regime, vol_20d, vol_60d, vol_ratio

def get_regime_weights(regime):
    """Return component weights for given regime"""
    weights = {
        'LOW_VOL': {
            'momentum': 0.35,
            'trend': 0.25,
            'volatility': 0.15,
            'volume': 0.15,
            'relative_strength': 0.10,
            'oversold': 0.00,
        },
        'NORMAL': {
            'momentum': 0.30,
            'trend': 0.25,
            'volatility': 0.20,
            'volume': 0.15,
            'relative_strength': 0.10,
            'oversold': 0.00,
        },
        'HIGH_VOL': {
            'momentum': 0.15,
            'trend': 0.20,
            'volatility': 0.30,
            'volume': 0.15,
            'relative_strength': 0.10,
            'oversold': 0.10,
        },
        'CRISIS': {
            'momentum': 0.05,
            'trend': 0.15,
            'volatility': 0.30,
            'volume': 0.15,
            'relative_strength': 0.10,
            'oversold': 0.25,
        },
    }
    return weights.get(regime, weights['NORMAL'])

if __name__ == '__main__':
    detector = RegimeDetector()
    regime, vol_20, vol_60, ratio = detector.detect_regime()
    print(f"Regime: {regime}")
    print(f"  20d vol: {vol_20:.2f}%")
    print(f"  60d vol: {vol_60:.2f}%")
    print(f"  Ratio: {ratio:.3f}")
    detector.close()
