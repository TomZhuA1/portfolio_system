#!/usr/bin/env python3
"""
Daily portfolio ranking orchestrator using regime-aware composite scoring.
Runs at 4 PM ET daily.
"""
import sys
import json
from datetime import datetime
from composite_ranker import CompositeRanker

def format_output(top_30, stats):
    """Format results for Telegram output"""
    messages = []
    
    # Header with regime info
    regime = stats['regime']
    regime_emoji = {
        'LOW_VOL': '📈',
        'NORMAL': '➡️',
        'HIGH_VOL': '📊',
        'CRISIS': '⛔'
    }
    
    header = f"""
{regime_emoji.get(regime, '📊')} PORTFOLIO RECOMMENDATION - {datetime.now().strftime('%Y-%m-%d')}

🎯 STRATEGY: Top 30 regime-aware selections
📈 REGIME: {regime} (20d vol: {stats['vol_20d']:.1f}%, 60d vol: {stats['vol_60d']:.1f}%)

🔝 TOP 10 SELECTIONS:
"""
    messages.append(header)
    
    # Top 10 details
    top_10_text = ""
    for i, stock in enumerate(top_30[:10], 1):
        ticker = stock['ticker']
        score = stock['composite']
        price = stock['metrics']['current_price']
        ret_63 = stock['metrics']['return_63d']
        vol = stock['metrics']['volatility']
        rsi = stock['metrics']['rsi_14']
        sector = "N/A"  # TODO: Load from sectors JSON
        
        top_10_text += f"{i:2d}. {ticker:6s} | ${price:8.2f} | Score: {score:.3f} | RSI: {rsi:.0f}\n"
        top_10_text += f"    63d return: {ret_63:+6.2f}% | Vol: {vol:5.1f}% | Components: "
        top_10_text += f"Mom={stock['components']['momentum']:.0f} Trend={stock['components']['trend']:.0f}\n"
    
    messages.append(top_10_text)
    
    # Bottom 10 to avoid (if desired)
    # ... could add risk warnings here
    
    # Summary stats
    summary = f"""
📊 PORTFOLIO STATS:
  • Stocks Analyzed: ~2,413
  • Selected (regime-adjusted): {stats['total_scored']}
  • Filtered out: {stats['total_filtered']}
  • Top 30 (sector-neutral): {len(top_30)}
  • Regime Weights: Mom={stats['regime_weights']['momentum']:.0%} Trend={stats['regime_weights']['trend']:.0%} Vol={stats['regime_weights']['volatility']:.0%}

⏱️ REBALANCING:
  • Daily rescore: Every 4 PM ET
  • Position exits: Drops below 200d SMA, vol spike >2×, composite <40th percentile
  • Allocation: Equal weight (1/{len(top_30)} = {100/len(top_30):.1f}% per stock)
"""
    messages.append(summary)
    
    return messages

def main():
    print("="*80)
    print("DAILY PORTFOLIO RANKING - REGIME-AWARE COMPOSITE SCORING")
    print("="*80)
    print(f"Start time: {datetime.now().isoformat()}\n")
    
    try:
        ranker = CompositeRanker()
        top_30, stats = ranker.rank_all()
        ranker.close()
        
        # Format output
        messages = format_output(top_30, stats)
        
        # Save results
        output = {
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'regime': stats['regime'],
            'top_30': [
                {
                    'rank': i+1,
                    'ticker': stock['ticker'],
                    'composite_score': stock['composite'],
                    'components': stock['components'],
                    'metrics': stock['metrics'],
                }
                for i, stock in enumerate(top_30)
            ],
            'stats': stats,
            'messages': messages,
        }
        
        with open('last_ranking.json', 'w') as f:
            json.dump(output, f, indent=2)
        
        print("\n" + "="*80)
        print("RESULTS")
        print("="*80)
        for msg in messages:
            print(msg)
        
        print(f"\n✅ Ranking complete. Results saved to last_ranking.json")
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
