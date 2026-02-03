#!/usr/bin/env python3
"""
Generate daily portfolio recommendation report.
Formats data, creates visualizations, prepares for delivery.
"""

import pandas as pd
from datetime import datetime
from phase1_signals import calculate_signals, get_stock_data, generate_recommendation

def format_report(recommendation):
    """Format recommendation into human-readable report."""
    
    top_50 = recommendation['top_50']
    bottom_50 = recommendation['bottom_50']
    
    # Build report sections
    report = {
        'title': f"🎯 PORTFOLIO RECOMMENDATION - {datetime.now().strftime('%Y-%m-%d')}",
        'timestamp': datetime.now(),
        'sections': []
    }
    
    # Section 1: Portfolio allocation
    section1 = "📊 RECOMMENDED ALLOCATION\n"
    section1 += "─" * 50 + "\n"
    section1 += "Strategy: Top 50 stocks by composite score\n"
    section1 += "Position size: 2.0% each (100% portfolio)\n"
    section1 += f"Total stocks: {len(recommendation['all_scores'])}\n"
    section1 += f"Coverage: {len(top_50)} selected (~11% of market)\n"
    report['sections'].append(('ALLOCATION', section1))
    
    # Section 2: Top 20 buys
    section2 = "🔝 TOP 20 BUYS\n"
    section2 += "─" * 50 + "\n"
    for idx, row in top_50.head(20).iterrows():
        section2 += f"{idx+1:2d}. {row['ticker']:6s} | Price: ${row['current_price']:8.2f} | "
        section2 += f"Momentum: {row['momentum_pct']:+6.2f}% | Vol: {row['volatility']:5.2f}\n"
    report['sections'].append(('TOP_BUYS', section2))
    
    # Section 3: Bottom 20 (to avoid)
    section3 = "🔻 TOP 20 AVOID\n"
    section3 += "─" * 50 + "\n"
    for idx, row in bottom_50.head(20).iterrows():
        section3 += f"{idx+1:2d}. {row['ticker']:6s} | Price: ${row['current_price']:8.2f} | "
        section3 += f"Momentum: {row['momentum_pct']:+6.2f}% | Vol: {row['volatility']:5.2f}\n"
    report['sections'].append(('BOTTOM_AVOIDS', section3))
    
    # Section 4: Portfolio metrics
    section4 = "📈 PORTFOLIO METRICS\n"
    section4 += "─" * 50 + "\n"
    section4 += f"Avg Momentum (Top 50): {top_50['momentum_pct'].mean():+.2f}%\n"
    section4 += f"Avg Volatility (Top 50): {top_50['volatility'].mean():.2f} (annualized)\n"
    section4 += f"Median Quality Score: {top_50['quality_score'].median():.3f}\n"
    section4 += f"Avg Composite Score: {top_50['composite_score'].mean():.3f}\n"
    report['sections'].append(('METRICS', section4))
    
    # Section 5: Sector distribution (rough)
    section5 = "🏢 STOCKS BY CATEGORY\n"
    section5 += "─" * 50 + "\n"
    section5 += "Tech/Software: NVDA, AAPL, MSFT, META, GOOG, ADBE, CRWD, DDOG, NET...\n"
    section5 += "Finance: JPM, GS, BLK, SCHW, AXP...\n"
    section5 += "Healthcare: JNJ, PFE, LLY, VRTX...\n"
    section5 += "Industrial: BA, CAT, MMM, RTX...\n"
    section5 += "(See full list in database)\n"
    report['sections'].append(('SECTORS', section5))
    
    return report

def print_report(report):
    """Print full report to console."""
    print("\n" + "=" * 80)
    print(report['title'])
    print("=" * 80)
    for section_name, section_text in report['sections']:
        print("\n" + section_text)
    print("\n" + "=" * 80)

def save_report_to_file(report, filename=None):
    """Save report to text file."""
    if not filename:
        filename = f"portfolio_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    with open(filename, 'w') as f:
        f.write(report['title'] + "\n")
        f.write("=" * 80 + "\n\n")
        for section_name, section_text in report['sections']:
            f.write(section_text + "\n\n")
    
    return filename

def main():
    print("Generating daily report...")
    
    # Get data and generate recommendation
    df = get_stock_data()
    scores = calculate_signals(df)
    recommendation = generate_recommendation(scores)
    
    # Format report
    report = format_report(recommendation)
    
    # Print and save
    print_report(report)
    filename = save_report_to_file(report)
    print(f"\n✅ Report saved to: {filename}")
    
    return report

if __name__ == "__main__":
    main()
