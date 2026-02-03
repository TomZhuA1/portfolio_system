#!/usr/bin/env python3
"""
Daily portfolio recommendation job.
Runs at 4 PM ET (market close + 30 min).
Generates recommendation and sends via Telegram.
"""

import sys
import json
from datetime import datetime
from phase1_signals import get_stock_data, calculate_signals, generate_recommendation
from daily_report_generator import format_report, save_report_to_file
from telegram_notifier import format_telegram_message

def run_daily_job():
    """
    Main daily job:
    1. Fetch latest data
    2. Calculate signals
    3. Generate recommendation
    4. Format report
    5. Send via Telegram
    6. Save to history
    """
    
    print("=" * 80)
    print(f"DAILY PORTFOLIO JOB - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    try:
        # Step 1: Get data
        print("\n[1/5] Fetching stock data...")
        df = get_stock_data()
        print(f"  ✓ Loaded {len(df)} price records for {df['ticker'].nunique()} stocks")
        
        # Step 2: Calculate signals
        print("\n[2/5] Calculating signals...")
        scores = calculate_signals(df)
        print(f"  ✓ Scored {len(scores)} stocks")
        print(f"    - Top scorer: {scores.iloc[0]['ticker']} ({scores.iloc[0]['composite_score']:.3f})")
        print(f"    - Bottom scorer: {scores.iloc[-1]['ticker']} ({scores.iloc[-1]['composite_score']:.3f})")
        
        # Step 3: Generate recommendation
        print("\n[3/5] Generating recommendation...")
        recommendation = generate_recommendation(scores)
        print(f"  ✓ Selected top 50 stocks")
        print(f"    - Avg momentum: {recommendation['top_50']['momentum_pct'].mean():+.2f}%")
        print(f"    - Avg volatility: {recommendation['top_50']['volatility'].mean():.2f}")
        
        # Step 4: Format report
        print("\n[4/5] Formatting report...")
        report = format_report(recommendation)
        report_file = save_report_to_file(report)
        print(f"  ✓ Report saved to: {report_file}")
        
        # Step 5: Prepare Telegram messages
        print("\n[5/5] Preparing Telegram messages...")
        telegram_msgs = format_telegram_message(recommendation)
        print(f"  ✓ Generated {len(telegram_msgs)} Telegram messages")
        
        # Save recommendation to JSON for delivery
        output = {
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'recommendation': {
                'top_50': recommendation['top_50'][['ticker', 'current_price', 'momentum_pct', 'volatility', 'composite_score']].head(20).to_dict('records'),
                'bottom_50': recommendation['bottom_50'][['ticker', 'current_price', 'momentum_pct', 'volatility', 'composite_score']].head(20).to_dict('records'),
                'stats': recommendation['stats'],
            },
            'telegram_messages': telegram_msgs,
            'report_file': report_file,
        }
        
        # Save to file for logging
        with open('last_recommendation.json', 'w') as f:
            json.dump(output, f, indent=2, default=str)
        
        print("\n" + "=" * 80)
        print("✅ JOB COMPLETE")
        print("=" * 80)
        print(f"\nRecommendation ready for Telegram delivery:")
        print(f"  • Report file: {report_file}")
        print(f"  • JSON output: last_recommendation.json")
        print(f"  • Messages: {len(telegram_msgs)} to send")
        
        return output
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        print("\nFull traceback:")
        import traceback
        traceback.print_exc()
        return {'status': 'error', 'error': str(e)}

if __name__ == "__main__":
    result = run_daily_job()
    sys.exit(0 if result['status'] == 'success' else 1)
