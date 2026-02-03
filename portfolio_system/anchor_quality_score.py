#!/usr/bin/env python3
"""
ANCHOR Strategy - Quality Assessment Module
Identifies fundamentally strong companies using price-based proxies.
(Fundamentals integration ready but using price proxies for now)
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

class QualityScorer:
    """Assess quality of stocks using price-based proxies"""
    
    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
    
    def close(self):
        if self.conn:
            self.cursor.close()
            self.conn.close()
    
    def get_ohlcv_history(self, ticker, days=1260):
        """Fetch 3+ years of daily data"""
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
    
    def get_monthly_returns(self, prices):
        """Convert daily prices to monthly returns"""
        # Assume roughly 21 trading days per month
        monthly_returns = []
        for i in range(0, len(prices) - 21, 21):
            month_start = prices[i]
            month_end = prices[i + 21]
            monthly_ret = (month_end - month_start) / month_start
            monthly_returns.append(monthly_ret)
        return monthly_returns
    
    def score_trend_consistency(self, prices):
        """1A: Trend Consistency (3-year view) - positive months ratio"""
        if len(prices) < 252:
            return 50.0
        
        monthly_returns = self.get_monthly_returns(prices)
        if len(monthly_returns) < 12:
            return 50.0
        
        # Use last 36 months if available
        monthly_returns = monthly_returns[-36:] if len(monthly_returns) >= 36 else monthly_returns
        
        positive_months = sum(1 for ret in monthly_returns if ret > 0)
        positive_ratio = positive_months / len(monthly_returns)
        
        # Score: 55%+ is good (quality signal)
        score = (positive_ratio * 100) if positive_ratio > 0.4 else (positive_ratio * 50)
        return min(100, score)
    
    def score_long_term_risk_adjusted(self, prices):
        """1A: 3-year Sharpe ratio proxy"""
        if len(prices) < 252:
            return 50.0
        
        # Use last 252+ days (minimum 1 year)
        period = min(len(prices), 756)  # 3 years ~ 756 days
        period_prices = prices[-period:]
        
        returns = [(period_prices[i+1] - period_prices[i]) / period_prices[i] 
                  for i in range(len(period_prices)-1)]
        
        total_return = (period_prices[-1] - period_prices[0]) / period_prices[0]
        avg_return = np.mean(returns)
        vol = np.std(returns)
        
        # Risk-free proxy: 0.05 annual / 252 days
        risk_free_daily = 0.05 / 252
        excess_return = avg_return - risk_free_daily
        
        sharpe = (excess_return / vol * math.sqrt(252)) if vol > 0 else 0
        
        # Cap Sharpe at reasonable range for scoring
        sharpe_score = 50 + (sharpe * 10)  # Normalize
        return min(100, max(0, sharpe_score))
    
    def score_drawdown_resilience(self, prices):
        """1A: Max drawdown and recovery speed"""
        if len(prices) < 252:
            return 50.0
        
        # Max drawdown over full history
        peak = prices[0]
        max_dd = 0
        for price in prices:
            if price > peak:
                peak = price
            dd = (price - peak) / peak
            if dd < max_dd:
                max_dd = dd
        
        # Assess recovery speed (simplified)
        # If max_dd > -40%, penalize; if close to 0, reward
        if max_dd > -0.10:
            dd_score = 100
        elif max_dd > -0.25:
            dd_score = 80
        elif max_dd > -0.40:
            dd_score = 60
        else:
            dd_score = 30
        
        return dd_score
    
    def score_price_stability(self, prices):
        """1A: Earnings volatility proxy - quarterly return stability"""
        if len(prices) < 252:
            return 50.0
        
        # Divide into ~4 quarter blocks, measure volatility
        quarter_len = len(prices) // 4
        if quarter_len < 20:
            return 50.0
        
        quarter_returns = []
        for i in range(0, len(prices) - quarter_len, quarter_len):
            q_start = prices[i]
            q_end = prices[i + quarter_len]
            q_ret = (q_end - q_start) / q_start
            quarter_returns.append(q_ret)
        
        # Lower volatility of quarterly returns = more predictable
        if quarter_returns:
            qtr_vol = np.std(quarter_returns)
            # Invert: low vol = high score
            stability_score = 100 - (qtr_vol * 100)
            return min(100, max(0, stability_score))
        
        return 50.0
    
    def score_quality(self, ticker):
        """Combined price-based quality score"""
        try:
            prices = self.get_ohlcv_history(ticker, 1260)
            if len(prices) < 252:
                return None  # Insufficient history
            
            prices_only = [row['close'] for row in prices]
            
            # Component scores
            trend_consistency = self.score_trend_consistency(prices_only)
            sharpe_3y = self.score_long_term_risk_adjusted(prices_only)
            dd_resilience = self.score_drawdown_resilience(prices_only)
            price_stability = self.score_price_stability(prices_only)
            
            # Weighted combination
            quality_score = (
                0.30 * trend_consistency +
                0.30 * sharpe_3y +
                0.25 * dd_resilience +
                0.15 * price_stability
            )
            
            return {
                'quality_score': quality_score,
                'trend_consistency': trend_consistency,
                'sharpe_3y': sharpe_3y,
                'dd_resilience': dd_resilience,
                'price_stability': price_stability,
            }
        except Exception as e:
            print(f"Error scoring quality for {ticker}: {e}")
            return None

if __name__ == '__main__':
    scorer = QualityScorer()
    # Test with AAPL
    result = scorer.score_quality('AAPL')
    if result:
        print(f"AAPL Quality Score: {result['quality_score']:.1f}")
        print(f"  Trend Consistency: {result['trend_consistency']:.1f}")
        print(f"  Sharpe 3Y: {result['sharpe_3y']:.1f}")
        print(f"  DD Resilience: {result['dd_resilience']:.1f}")
        print(f"  Price Stability: {result['price_stability']:.1f}")
    scorer.close()
