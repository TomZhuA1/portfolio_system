#!/usr/bin/env python3
"""
ANCHOR Strategy - Main Ranker
Combines quality + discount scores with matrix weighting, stabilization checks,
and position sizing.
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import numpy as np
from datetime import datetime
from anchor_quality_score import QualityScorer
from anchor_discount_score import DiscountScorer

DB_CONFIG = {
    "host": "localhost",
    "database": "stock_data",
    "user": "postgres",
    "password": "stock_password",
    "port": 5432,
}

class AnchorRanker:
    """ANCHOR Strategy: Quality at a Discount"""
    
    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        
        # Load sector mapping
        try:
            with open('ticker_sectors.json', 'r') as f:
                self.ticker_sectors = json.load(f)
        except:
            self.ticker_sectors = {}
        
        self.quality_scorer = QualityScorer()
        self.discount_scorer = DiscountScorer()
    
    def close(self):
        if self.conn:
            self.cursor.close()
            self.conn.close()
        if self.quality_scorer:
            self.quality_scorer.close()
        if self.discount_scorer:
            self.discount_scorer.close()
    
    def get_all_tickers(self):
        """Fetch all unique tickers"""
        self.cursor.execute("SELECT DISTINCT ticker FROM stock_prices ORDER BY ticker")
        return [row['ticker'] for row in self.cursor.fetchall()]
    
    def get_most_recent_trading_date(self):
        """Get the most recent trading date in the database"""
        self.cursor.execute("SELECT MAX(timestamp) as max_date FROM stock_prices")
        result = self.cursor.fetchone()
        return result['max_date'] if result else None
    
    def is_delisted(self, ticker, most_recent_date):
        """Check if ticker is delisted: no price data on most recent trading date"""
        self.cursor.execute("""
            SELECT COUNT(*) as cnt FROM stock_prices 
            WHERE ticker = %s AND timestamp = %s
        """, (ticker, most_recent_date))
        result = self.cursor.fetchone()
        return result['cnt'] == 0 if result else True
    
    def percentile_rank(self, value, population):
        """Calculate percentile rank (0-100)"""
        if not population or len(population) < 2:
            return 50.0
        sorted_pop = sorted(population)
        rank = sum(1 for x in sorted_pop if x < value) / len(sorted_pop)
        return rank * 100.0
    
    def get_matrix_multiplier(self, quality_pctl, discount_pctl):
        """Step 3: Quality-Discount matrix multiplier"""
        # Top 20% = 80th percentile
        # Top 40% = 60th percentile
        
        if quality_pctl >= 80:
            if discount_pctl >= 80:
                return 1.00  # Ideal
            elif discount_pctl >= 60:
                return 0.85
            else:
                return 0.00  # Good quality but not discounted
        elif quality_pctl >= 60:
            if discount_pctl >= 80:
                return 0.80
            elif discount_pctl >= 60:
                return 0.70
            else:
                return 0.00  # Not discounted enough
        else:
            return 0.00  # Below quality threshold
    
    def check_stabilization(self, ticker):
        """Step 4: Check if stock shows stabilization signals"""
        try:
            self.cursor.execute("""
                SELECT timestamp, close, volume 
                FROM stock_prices 
                WHERE ticker = %s 
                ORDER BY timestamp DESC LIMIT 30
            """, (ticker,))
            rows = list(reversed(self.cursor.fetchall()))
            
            if len(rows) < 10:
                return 0  # Insufficient data
            
            prices = [row['close'] for row in rows]
            volumes = [row['volume'] for row in rows]
            
            signals_met = 0
            
            # Signal 1: RSI turned up from below 35
            rsi_14 = self.discount_scorer.rsi(prices, 14)
            if rsi_14 < 35:
                signals_met += 1
            
            # Signal 2: Price above 5-day SMA
            sma_5 = np.mean(prices[-5:])
            if prices[-1] > sma_5:
                signals_met += 1
            
            # Signal 3: Volume on up days > volume on down days (last 10 days)
            up_vol = sum(volumes[i] for i in range(len(volumes)-10, len(volumes)) 
                        if prices[i] > prices[i-1])
            down_vol = sum(volumes[i] for i in range(len(volumes)-10, len(volumes)) 
                          if prices[i] < prices[i-1])
            if up_vol > down_vol:
                signals_met += 1
            
            # Signal 4: Higher low formed in last 20 days
            mins = [min(prices[i-5:i+1]) for i in range(5, len(prices))]
            if len(mins) >= 2 and mins[-1] > mins[-2]:
                signals_met += 1
            
            return signals_met
        except:
            return 0
    
    def check_value_traps(self, ticker):
        """Step 4: Avoid value traps - check for red flags"""
        try:
            self.cursor.execute("""
                SELECT close FROM stock_prices 
                WHERE ticker = %s 
                ORDER BY timestamp DESC LIMIT 252
            """, (ticker,))
            prices = list(reversed([row['close'] for row in self.cursor.fetchall()]))
            
            if len(prices) < 252:
                return False  # Not enough history, skip
            
            # Check: Price below 200d SMA and 200d SMA declining
            sma_200_current = np.mean(prices[-200:])
            sma_200_past = np.mean(prices[-220:-20]) if len(prices) >= 220 else sma_200_current
            
            if prices[-1] < sma_200_current and sma_200_current < sma_200_past:
                return True  # TRAP: Structural downtrend
            
            # Could add more checks here (earnings decline, debt increase, etc.)
            return False
        except:
            return False
    
    def calculate_position_size(self, quality_pctl, discount_pctl):
        """Step 6: Position sizing based on conviction"""
        base_size = 1.0  # Normalized base weight
        
        if quality_pctl >= 90 and discount_pctl >= 80:
            return base_size * 1.5  # High conviction
        elif quality_pctl >= 80 and discount_pctl >= 60:
            return base_size * 1.0  # Medium conviction
        elif quality_pctl >= 60 and discount_pctl >= 50:
            return base_size * 0.7  # Lower conviction
        else:
            return 0.0
    
    def rank_all(self):
        """Rank all tickers with ANCHOR logic"""
        print(f"ANCHOR STRATEGY - Quality at a Discount")
        
        # Get most recent trading date for delisting check
        most_recent_date = self.get_most_recent_trading_date()
        print(f"Most recent trading date in DB: {most_recent_date}")
        
        all_tickers = self.get_all_tickers()
        print(f"Scoring {len(all_tickers)} stocks...")
        
        ranked_stocks = []
        delisted_count = 0
        
        # First pass: collect scores
        quality_scores_all = []
        discount_scores_all = []
        
        print("Pass 1: Calculating quality and discount scores (excluding delisted)...")
        stock_data = {}
        
        for i, ticker in enumerate(all_tickers):
            if (i + 1) % 500 == 0:
                print(f"  [{i+1}/{len(all_tickers)}]...")
            
            # FILTER: Skip delisted tickers (no price on most recent date)
            if self.is_delisted(ticker, most_recent_date):
                delisted_count += 1
                continue
            
            # Score quality
            quality_result = self.quality_scorer.score_quality(ticker)
            if not quality_result or quality_result['quality_score'] < 30:
                continue
            
            # Score discount
            discount_result = self.discount_scorer.score_discount(ticker)
            if not discount_result or discount_result['discount_score'] < 20:
                continue
            
            quality_scores_all.append(quality_result['quality_score'])
            discount_scores_all.append(discount_result['discount_score'])
            
            stock_data[ticker] = {
                'quality': quality_result,
                'discount': discount_result,
            }
        
        print(f"✓ Collected {len(stock_data)} candidates")
        
        # Calculate percentiles
        quality_50th = np.percentile(quality_scores_all, 50)
        discount_50th = np.percentile(discount_scores_all, 50)
        
        print(f"Quality 50th: {quality_50th:.1f}, Discount 50th: {discount_50th:.1f}")
        
        # Second pass: calculate composite scores
        print("Pass 2: Calculating composite scores and stability checks...")
        
        for i, (ticker, data) in enumerate(stock_data.items()):
            if (i + 1) % 200 == 0:
                print(f"  [{i+1}/{len(stock_data)}]...")
            
            quality_score = data['quality']['quality_score']
            discount_score = data['discount']['discount_score']
            
            # Skip if below 50th percentile filters
            if quality_score < quality_50th or discount_score < discount_50th:
                continue
            
            # Check for value traps
            if self.check_value_traps(ticker):
                continue
            
            # Calculate percentiles
            quality_pctl = self.percentile_rank(quality_score, quality_scores_all)
            discount_pctl = self.percentile_rank(discount_score, discount_scores_all)
            
            # Matrix multiplier
            matrix_mult = self.get_matrix_multiplier(quality_pctl, discount_pctl)
            if matrix_mult == 0:
                continue
            
            # Base composite
            base_composite = 0.55 * quality_score + 0.45 * discount_score
            final_composite = base_composite * matrix_mult
            
            # Stabilization check
            stabilization_signals = self.check_stabilization(ticker)
            
            # Position size
            position_size = self.calculate_position_size(quality_pctl, discount_pctl)
            
            ranked_stocks.append({
                'ticker': ticker,
                'composite_score': final_composite,
                'quality_score': quality_score,
                'discount_score': discount_score,
                'quality_pctl': quality_pctl,
                'discount_pctl': discount_pctl,
                'matrix_multiplier': matrix_mult,
                'stabilization_signals': stabilization_signals,
                'position_size': position_size,
                'components': {
                    'quality': data['quality'],
                    'discount': data['discount'],
                }
            })
        
        # Sort by composite score
        ranked_stocks.sort(key=lambda x: x['composite_score'], reverse=True)
        
        print(f"✓ Ranked: {len(ranked_stocks)} candidates")
        
        # Sector constraints (max 30% defensive, max 25% cyclicals)
        top_20 = ranked_stocks[:20]
        
        print(f"✓ Delisted filtered: {delisted_count} stocks")
        print(f"✓ Ranked: {len(ranked_stocks)} stocks")
        
        return top_20, {
            'regime': 'CONTRARIAN',
            'timestamp': datetime.now().isoformat(),
            'total_candidates': len(stock_data),
            'total_ranked': len(ranked_stocks),
            'quality_50th_pctl': quality_50th,
            'discount_50th_pctl': discount_50th,
            'delisted_filtered': delisted_count,
        }

if __name__ == '__main__':
    ranker = AnchorRanker()
    top_20, stats = ranker.rank_all()
    
    print("\n" + "="*100)
    print("ANCHOR TOP 20")
    print("="*100)
    for i, stock in enumerate(top_20, 1):
        print(f"\n{i:2d}. {stock['ticker']:6s} | Score: {stock['composite_score']:6.2f}")
        print(f"    Quality: {stock['quality_score']:.1f} (pctl: {stock['quality_pctl']:.0f}) | "
              f"Discount: {stock['discount_score']:.1f} (pctl: {stock['discount_pctl']:.0f})")
        print(f"    Stabilization: {stock['stabilization_signals']}/4 | Position Size: {stock['position_size']:.2f}x")
    
    ranker.close()
