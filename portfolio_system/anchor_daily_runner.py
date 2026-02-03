#!/usr/bin/env python3
"""
ANCHOR Daily Runner
Executes ANCHOR strategy and saves results.
"""
import sys
import json
from datetime import datetime
from anchor_ranker import AnchorRanker

def format_output(top_20, stats):
    """Format ANCHOR results for output"""
    messages = []
    
    header = f"""
🎯 ANCHOR STRATEGY - {datetime.now().strftime('%Y-%m-%d')}

💎 STRATEGY: Quality at a Discount (Contrarian approach)
🎯 GOAL: Identify fundamentally strong companies with temporary weakness

📊 TOP 10 SELECTIONS:
"""
    messages.append(header)
    
    # Top 10 details
    top_10_text = ""
    for i, stock in enumerate(top_20[:10], 1):
        ticker = stock['ticker']
        score = stock['composite_score']
        quality = stock['quality_score']
        discount = stock['discount_score']
        stab = stock['stabilization_signals']
        pos_size = stock['position_size']
        
        quality_comp = stock['components']['quality']
        discount_comp = stock['components']['discount']
        
        top_10_text += f"{i:2d}. {ticker:6s} | Score: {score:6.2f} | Quality: {quality:.1f} | Discount: {discount:.1f}\n"
        top_10_text += f"    Stabilization: {stab}/4 | Position Size: {pos_size:.2f}x | "
        top_10_text += f"Pullback: {discount_comp['pullback_pct']:.1f}% from 52w high\n"
    
    messages.append(top_10_text)
    
    # Strategy stats
    summary = f"""
📈 STRATEGY STATS:
  • Total candidates screened: {stats['total_candidates']}
  • Passed quality filter (50th+ pctl): ~{stats['total_ranked']}
  • Top 20 selected (with sector constraints): {len(top_20)}
  
💡 ANCHOR LOGIC:
  • Contrarian to momentum (diversification)
  • 3-year quality assessment vs temporary weakness
  • Requires stabilization signals (2+/4) before entry
  • Position sizing by conviction level
  
⏱️ MANAGEMENT:
  • Rescore: Daily
  • Hold period: 3-6 months (longer-term)
  • Exit: Quality drops, discount closed, or stabilization fails

⚠️ RISK:
  • Value trap avoidance: checks structural downtrends
  • Momentum divergence required (long-term strength)
  • Requires RSI+volume+MA confirmation
"""
    messages.append(summary)
    
    return messages

def main():
    print("="*80)
    print("ANCHOR DAILY RUNNER - Quality at a Discount")
    print("="*80)
    print(f"Start: {datetime.now().isoformat()}\n")
    
    try:
        ranker = AnchorRanker()
        top_20, stats = ranker.rank_all()
        ranker.close()
        
        if len(top_20) == 0:
            print("⚠️  No stocks met ANCHOR criteria today")
            return 1
        
        # Format output
        messages = format_output(top_20, stats)
        
        # Save results
        output = {
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'strategy': 'ANCHOR',
            'top_20': [
                {
                    'rank': i+1,
                    'ticker': stock['ticker'],
                    'composite_score': stock['composite_score'],
                    'quality_score': stock['quality_score'],
                    'discount_score': stock['discount_score'],
                    'quality_pctl': stock['quality_pctl'],
                    'discount_pctl': stock['discount_pctl'],
                    'stabilization_signals': stock['stabilization_signals'],
                    'position_size': stock['position_size'],
                    'components': {
                        'quality': stock['components']['quality'],
                        'discount': stock['components']['discount'],
                    }
                }
                for i, stock in enumerate(top_20)
            ],
            'stats': stats,
            'messages': messages,
        }
        
        with open('anchor_ranking.json', 'w') as f:
            json.dump(output, f, indent=2)
        
        print("\n" + "="*80)
        print("ANCHOR RESULTS")
        print("="*80)
        for msg in messages:
            print(msg)
        
        print(f"\n✅ ANCHOR ranking complete. Results saved to anchor_ranking.json")
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
