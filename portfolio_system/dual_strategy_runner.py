#!/usr/bin/env python3
"""
Dual Strategy Runner: SURGE + ANCHOR
Runs both strategies daily and checks correlation/overlap.
"""
import sys
import json
from datetime import datetime
import subprocess

def run_surge():
    """Run SURGE strategy"""
    print("\n" + "="*80)
    print("RUNNING SURGE (Momentum)")
    print("="*80)
    result = subprocess.run(['python3', 'daily_cron_runner.py'], 
                          capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        print(f"❌ SURGE failed: {result.stderr}")
        return None
    
    try:
        with open('last_ranking.json', 'r') as f:
            return json.load(f)
    except:
        return None

def run_anchor():
    """Run ANCHOR strategy"""
    print("\n" + "="*80)
    print("RUNNING ANCHOR (Quality at Discount)")
    print("="*80)
    result = subprocess.run(['python3', 'anchor_daily_runner.py'], 
                          capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        print(f"❌ ANCHOR failed: {result.stderr}")
        return None
    
    try:
        with open('anchor_ranking.json', 'r') as f:
            return json.load(f)
    except:
        return None

def check_overlap(surge_data, anchor_data):
    """Check overlap between strategies"""
    if not surge_data or not anchor_data:
        return None
    
    surge_tickers = set(s['ticker'] for s in surge_data.get('top_30', [])[:20])
    anchor_tickers = set(s['ticker'] for s in anchor_data.get('top_20', []))
    
    overlap = surge_tickers & anchor_tickers
    overlap_pct = (len(overlap) / min(len(surge_tickers), len(anchor_tickers)) * 100) if surge_tickers else 0
    
    return {
        'surge_tickers': sorted(list(surge_tickers)),
        'anchor_tickers': sorted(list(anchor_tickers)),
        'overlap': sorted(list(overlap)),
        'overlap_count': len(overlap),
        'overlap_pct': overlap_pct,
        'status': 'GOOD' if overlap_pct < 30 else 'CAUTION' if overlap_pct < 40 else 'ALERT',
    }

def combine_portfolios(surge_data, anchor_data, overlap_analysis):
    """Combine both strategies into unified portfolio"""
    combined = []
    
    # Add SURGE top 15
    if surge_data and 'top_30' in surge_data:
        for i, stock in enumerate(surge_data['top_30'][:15], 1):
            combined.append({
                'rank': len(combined) + 1,
                'ticker': stock['ticker'],
                'strategy': 'SURGE',
                'strategy_rank': i,
                'score': stock['composite_score'],
                'allocation_pct': 2.0,  # 15 stocks = ~2% each from SURGE
            })
    
    # Add ANCHOR top 15 (skip if already in SURGE)
    if anchor_data and 'top_20' in anchor_data:
        surge_set = set(s['ticker'] for s in combined)
        count = 0
        for i, stock in enumerate(anchor_data['top_20'], 1):
            if count >= 15:
                break
            if stock['ticker'] not in surge_set:
                combined.append({
                    'rank': len(combined) + 1,
                    'ticker': stock['ticker'],
                    'strategy': 'ANCHOR',
                    'strategy_rank': i,
                    'score': stock['composite_score'],
                    'allocation_pct': 2.0,  # ~2% each from ANCHOR
                })
                count += 1
    
    return combined[:30]

def main():
    print("="*80)
    print("DUAL STRATEGY RUNNER: SURGE + ANCHOR")
    print("="*80)
    print(f"Start: {datetime.now().isoformat()}\n")
    
    # Run both strategies
    surge_data = run_surge()
    anchor_data = run_anchor()
    
    if not surge_data or not anchor_data:
        print("❌ One or both strategies failed")
        return 1
    
    print("\n" + "="*80)
    print("STRATEGY CORRELATION ANALYSIS")
    print("="*80)
    
    # Check overlap
    overlap = check_overlap(surge_data, anchor_data)
    
    if overlap:
        print(f"\nOverlap Analysis:")
        print(f"  SURGE top 20: {len(overlap['surge_tickers'])} tickers")
        print(f"  ANCHOR top 20: {len(overlap['anchor_tickers'])} tickers")
        print(f"  Overlap: {overlap['overlap_count']} stocks ({overlap['overlap_pct']:.1f}%)")
        print(f"  Status: {overlap['status']}")
        
        if overlap['overlap']:
            print(f"  Overlap tickers: {', '.join(overlap['overlap'][:5])}")
    
    # Combine portfolios
    combined = combine_portfolios(surge_data, anchor_data, overlap)
    
    # Save unified output
    dual_output = {
        'status': 'success',
        'timestamp': datetime.now().isoformat(),
        'surge': {
            'top_30': surge_data.get('top_30', [])[:20],
            'regime': surge_data.get('regime'),
        },
        'anchor': {
            'top_20': anchor_data.get('top_20', []),
        },
        'correlation': overlap,
        'combined_portfolio': combined,
    }
    
    with open('dual_strategy_output.json', 'w') as f:
        json.dump(dual_output, f, indent=2)
    
    # Display combined portfolio
    print("\n" + "="*80)
    print("COMBINED PORTFOLIO (30 stocks)")
    print("="*80)
    print(f"{'Rank':<5} {'Ticker':<8} {'Strategy':<10} {'Score':<8} {'Alloc':<6}")
    print("-" * 50)
    for stock in combined:
        print(f"{stock['rank']:<5} {stock['ticker']:<8} {stock['strategy']:<10} "
              f"{stock['score']:<8.2f} {stock['allocation_pct']:<6.1f}%")
    
    print(f"\n✅ Dual strategy run complete.")
    print(f"   SURGE: {len(overlap['surge_tickers'])} stocks")
    print(f"   ANCHOR: {len(overlap['anchor_tickers'])} stocks")
    print(f"   Overlap: {overlap['overlap_pct']:.1f}% ({overlap['status']})")
    print(f"   Combined: {len(combined)} stocks")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
