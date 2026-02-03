#!/usr/bin/env python3
"""
Main ranking engine: Combine component scores with regime weights, apply filters,
sector neutralization, and generate top 30 recommendations.
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import numpy as np
from datetime import datetime
from regime_detector import RegimeDetector, get_regime_weights
from component_scores import ComponentScorer

DB_CONFIG = {
    "host": "localhost",
    "database": "stock_data",
    "user": "postgres",
    "password": "stock_password",
    "port": 5432,
}

class CompositeRanker:
    """Rank all 2413 stocks with regime-aware composite scoring"""
    
    def __init__(self):
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        
        # Load sector mapping
        try:
            with open('ticker_sectors.json', 'r') as f:
                self.ticker_sectors = json.load(f)
        except:
            self.ticker_sectors = {}
        
        # Regime detection
        self.regime_detector = RegimeDetector()
        self.regime, self.vol_20, self.vol_60, self.vol_ratio = self.regime_detector.detect_regime()
        self.regime_weights = get_regime_weights(self.regime)
        
        # Component scorer
        self.scorer = ComponentScorer()
    
    def close(self):
        if self.conn:
            self.cursor.close()
            self.conn.close()
        if self.regime_detector:
            self.regime_detector.close()
        if self.scorer:
            self.scorer.close()
    
    def get_all_tickers(self):
        """Fetch all unique tickers from database"""
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
        return result['cnt'] == 0 if result else True  # Delisted if no data on latest date
    
    def has_sufficient_history(self, ticker):
        """Check if ticker has 252+ days of data"""
        self.cursor.execute("""
            SELECT COUNT(*) as cnt FROM stock_prices 
            WHERE ticker = %s
        """, (ticker,))
        result = self.cursor.fetchone()
        return result['cnt'] >= 252 if result else False
    
    def get_avg_dollar_volume(self, ticker):
        """Get 20-day average dollar volume"""
        self.cursor.execute("""
            SELECT AVG(close * volume) as avg_dv FROM (
                SELECT close, volume FROM stock_prices 
                WHERE ticker = %s 
                ORDER BY timestamp DESC LIMIT 20
            ) subq
        """, (ticker,))
        result = self.cursor.fetchone()
        return result['avg_dv'] or 0 if result else 0
    
    def get_current_price_and_52w(self, ticker):
        """Get current price and 52-week high/low"""
        self.cursor.execute("""
            SELECT close FROM stock_prices 
            WHERE ticker = %s 
            ORDER BY timestamp DESC LIMIT 1
        """, (ticker,))
        current = self.cursor.fetchone()
        current_price = current['close'] if current else None
        
        self.cursor.execute("""
            SELECT MAX(close) as high, MIN(close) as low FROM (
                SELECT close FROM stock_prices 
                WHERE ticker = %s 
                ORDER BY timestamp DESC LIMIT 252
            ) subq
        """, (ticker,))
        range_data = self.cursor.fetchone()
        high_52w = range_data['high'] if range_data else None
        low_52w = range_data['low'] if range_data else None
        
        return current_price, high_52w, low_52w
    
    def get_max_drawdown_252(self, ticker):
        """Get max drawdown from 252-day high"""
        self.cursor.execute("""
            SELECT MAX(close) as peak FROM (
                SELECT close FROM stock_prices 
                WHERE ticker = %s
                ORDER BY timestamp DESC LIMIT 252
            ) subq
        """, (ticker,))
        result = self.cursor.fetchone()
        peak = result['peak'] if result else None
        
        current_price, _, _ = self.get_current_price_and_52w(ticker)
        
        if peak and current_price:
            drawdown = (current_price - peak) / peak
            return drawdown
        return 0
    
    def apply_filters(self, ticker, most_recent_date):
        """Apply hard exclusion filters. Return True if PASS, False if FAIL"""
        
        # Filter 0: DELISTED CHECK - No price on most recent trading date
        if self.is_delisted(ticker, most_recent_date):
            return False, "DELISTED (no data on latest date)"
        
        # Filter 1: < 252 days history
        if not self.has_sufficient_history(ticker):
            return False, "Insufficient history"
        
        # Filter 2: Liquidity < $1M (20d avg dollar volume)
        avg_dv = self.get_avg_dollar_volume(ticker)
        if avg_dv < 1_000_000:
            return False, f"Low liquidity: ${avg_dv:,.0f}"
        
        # Filter 3: Price < $5
        current_price, _, _ = self.get_current_price_and_52w(ticker)
        if current_price is None or current_price < 5:
            return False, "Penny stock (<$5)"
        
        # Filter 4: Max drawdown > 50% from 252d high
        drawdown = self.get_max_drawdown_252(ticker)
        if drawdown < -0.50:
            return False, f"Severe drawdown: {drawdown*100:.1f}%"
        
        return True, "Pass"
    
    def check_trend_score(self, ticker):
        """Filter: EXCLUDE stocks with trend score = 100.0"""
        try:
            ohlcv = self.scorer.get_ohlcv(ticker, 252)
            if len(ohlcv) < 50:
                return True  # Pass if insufficient data
            
            prices = [row['close'] for row in ohlcv]
            trend_score = self.scorer.score_trend(prices)
            
            # REJECT if trend = 100.0 (perfect trend)
            if trend_score >= 99.9:  # Using 99.9 to account for floating point
                return False
            return True
        except:
            return True  # Pass if error
    
    def rank_stock(self, ticker):
        """Calculate composite score for a single stock"""
        # Get OHLCV data
        ohlcv = self.scorer.get_ohlcv(ticker, 252)
        if len(ohlcv) < 50:
            return None
        
        prices = [row['close'] for row in ohlcv]
        
        # Calculate component scores
        try:
            momentum = self.scorer.score_momentum(prices)
            trend = self.scorer.score_trend(prices)
            volatility = self.scorer.score_volatility(prices)
            volume = self.scorer.score_volume(ohlcv)
            relative_strength = self.scorer.score_relative_strength(ticker, prices, self.ticker_sectors.get(ticker, 'Unknown'))
            oversold = self.scorer.score_oversold(prices)
        except Exception as e:
            print(f"Error scoring {ticker}: {e}")
            return None
        
        # Apply regime weights
        composite = (
            self.regime_weights['momentum'] * momentum +
            self.regime_weights['trend'] * trend +
            self.regime_weights['volatility'] * volatility +
            self.regime_weights['volume'] * volume +
            self.regime_weights['relative_strength'] * relative_strength +
            self.regime_weights['oversold'] * oversold
        )
        
        # Get metrics for output
        current_price, high_52w, low_52w = self.get_current_price_and_52w(ticker)
        rsi_14 = self.scorer.rsi(prices, 14)
        sma_50 = np.mean(prices[-50:]) if len(prices) >= 50 else prices[-1]
        distance_50d = (prices[-1] - sma_50) / sma_50 if sma_50 > 0 else 0
        vol_60d = np.std([((prices[i+1] - prices[i]) / prices[i]) for i in range(len(prices)-60, len(prices)-1)]) * np.sqrt(252) * 100
        
        return {
            'ticker': ticker,
            'composite': composite,
            'components': {
                'momentum': momentum,
                'trend': trend,
                'volatility': volatility,
                'volume': volume,
                'relative_strength': relative_strength,
                'oversold': oversold,
            },
            'metrics': {
                'current_price': current_price,
                'return_63d': ((prices[-1] - prices[-63]) / prices[-63] * 100) if len(prices) >= 63 else 0,
                'volatility': vol_60d,
                'rsi_14': rsi_14,
                'distance_from_50d_ma': distance_50d * 100,
                'high_52w': high_52w,
                'low_52w': low_52w,
            }
        }
    
    def sector_neutralize(self, ranked_stocks):
        """Ensure no more than 4 stocks from same sector in top 30"""
        # Group by sector
        sector_counts = {}
        final_ranking = []
        demoted = []
        
        for stock in ranked_stocks:
            sector = self.ticker_sectors.get(stock['ticker'], 'Unknown')
            count = sector_counts.get(sector, 0)
            
            if count < 4:
                final_ranking.append(stock)
                sector_counts[sector] = count + 1
            else:
                demoted.append(stock)
        
        # Add demoted stocks if we're below 30
        final_ranking.extend(demoted[:max(0, 30 - len(final_ranking))])
        
        return final_ranking[:30]
    
    def rank_all(self):
        """Rank all tickers and return top 30 with sector neutralization"""
        print(f"Regime: {self.regime} (20d vol: {self.vol_20:.1f}%, 60d vol: {self.vol_60:.1f}%)")
        
        # Get most recent trading date for delisting check
        most_recent_date = self.get_most_recent_trading_date()
        print(f"Most recent trading date in DB: {most_recent_date}")
        print(f"Scoring {len(self.get_all_tickers())} stocks...")
        
        all_tickers = self.get_all_tickers()
        ranked_stocks = []
        filtered_count = 0
        delisted_count = 0
        
        for i, ticker in enumerate(all_tickers):
            if (i + 1) % 500 == 0:
                print(f"  [{i+1}/{len(all_tickers)}] Scored...")
            
            # Apply filters (including delisting check)
            passes_filter, reason = self.apply_filters(ticker, most_recent_date)
            if not passes_filter:
                if "DELISTED" in reason:
                    delisted_count += 1
                filtered_count += 1
                continue
            
            # Filter: EXCLUDE trend = 100.0
            if not self.check_trend_score(ticker):
                filtered_count += 1
                continue
            
            # Rank
            result = self.rank_stock(ticker)
            if result:
                ranked_stocks.append(result)
        
        # Sort by composite score
        ranked_stocks.sort(key=lambda x: x['composite'], reverse=True)
        
        # Sector neutralize
        top_30 = self.sector_neutralize(ranked_stocks)
        
        print(f"\n✓ Filtered: {filtered_count} stocks ({delisted_count} delisted)")
        print(f"✓ Ranked: {len(ranked_stocks)} stocks")
        print(f"✓ Top 30 (sector-neutral): {len(top_30)} stocks")
        
        return top_30, {
            'regime': self.regime,
            'vol_20d': self.vol_20,
            'vol_60d': self.vol_60,
            'vol_ratio': self.vol_ratio,
            'timestamp': datetime.now().isoformat(),
            'total_scored': len(ranked_stocks),
            'total_filtered': filtered_count,
            'delisted_filtered': delisted_count,
            'regime_weights': self.regime_weights,
        }

if __name__ == '__main__':
    ranker = CompositeRanker()
    top_30, stats = ranker.rank_all()
    
    print("\n" + "="*80)
    print("TOP 30 STOCKS")
    print("="*80)
    for i, stock in enumerate(top_30, 1):
        print(f"\n{i:2d}. {stock['ticker']:6s} | Score: {stock['composite']:6.2f}")
        print(f"    Price: ${stock['metrics']['current_price']:.2f} | RSI: {stock['metrics']['rsi_14']:.1f} | "
              f"Vol: {stock['metrics']['volatility']:.1f}%")
        print(f"    Components: Mom={stock['components']['momentum']:.0f} Trend={stock['components']['trend']:.0f} "
              f"Vol={stock['components']['volatility']:.0f} Vol={stock['components']['volume']:.0f}")
    
    ranker.close()
