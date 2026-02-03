#!/usr/bin/env python3
"""
Send daily portfolio recommendation via Telegram.
Formats report as readable Telegram messages.
"""

def format_telegram_message(report_dict):
    """Convert recommendation dict to Telegram-friendly format."""
    
    top_50 = report_dict['top_50']
    bottom_50 = report_dict['bottom_50']
    
    # Message 1: Header + Top 10 buys
    msg1 = f"""
🎯 PORTFOLIO RECOMMENDATION - {report_dict['timestamp'].strftime('%Y-%m-%d')}

📊 STRATEGY: Top 50 stocks (2% each)

🔝 TOP 10 BUYS:
"""
    for idx, row in top_50.head(10).iterrows():
        msg1 += f"{idx+1}. {row['ticker']} - ${row['current_price']:.2f} | Mom: {row['momentum_pct']:+.1f}% | Vol: {row['volatility']:.2f}\n"
    
    # Message 2: Bottom 10 + metrics
    msg2 = f"""
🔻 TOP 10 TO AVOID:
"""
    for idx, row in bottom_50.head(10).iterrows():
        msg2 += f"{idx+1}. {row['ticker']} - ${row['current_price']:.2f} | Mom: {row['momentum_pct']:+.1f}% | Vol: {row['volatility']:.2f}\n"
    
    msg2 += f"""
📈 METRICS:
  • Avg Momentum (Top 50): {top_50['momentum_pct'].mean():+.2f}%
  • Avg Volatility: {top_50['volatility'].mean():.2f}
  • Median Quality: {top_50['quality_score'].median():.3f}
  • Total Stocks: {len(report_dict['all_scores'])}
"""
    
    # Message 3: Full top 20 (for detailed view)
    msg3 = "📋 FULL TOP 20 BUYS:\n"
    for idx, row in top_50.head(20).iterrows():
        msg3 += f"{idx+1:2d}. {row['ticker']:6s} | ${row['current_price']:8.2f} | Composite: {row['composite_score']:.3f}\n"
    
    return [msg1, msg2, msg3]

def send_telegram(messages, channel_or_user):
    """Send messages via OpenClaw message tool."""
    # This will be called from the cron job
    # Messages are passed to the message tool
    return messages

def main():
    from phase1_signals import get_stock_data, calculate_signals, generate_recommendation
    
    print("Generating recommendation...")
    df = get_stock_data()
    scores = calculate_signals(df)
    recommendation = generate_recommendation(scores)
    
    print("Formatting Telegram messages...")
    messages = format_telegram_message(recommendation)
    
    print(f"\n📱 MESSAGE 1 (Header + Top 10):")
    print(messages[0])
    print(f"\n📱 MESSAGE 2 (Bottom 10 + Metrics):")
    print(messages[1])
    print(f"\n📱 MESSAGE 3 (Full Top 20):")
    print(messages[2])

if __name__ == "__main__":
    main()
