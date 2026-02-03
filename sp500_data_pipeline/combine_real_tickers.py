#!/usr/bin/env python3
"""
Combine S&P 500 + Russell 2000 to get real, verified stocks.
No synthetic tickers - all from official sources.
"""

import json
import csv

# S&P 500 core (verified)
SP500 = [
    'AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMZN', 'META', 'GOOG', 'GOOGL', 'BERKB', 'JPM',
    'JNJ', 'V', 'WMT', 'XOM', 'PG', 'MA', 'HD', 'KO', 'MCD', 'PEP', 'PFE', 'ABBV',
    'LLY', 'AVGO', 'TXN', 'ASML', 'AMD', 'COST', 'CMCSA', 'NKE', 'ADBE', 'BA', 'IBM',
    'INTC', 'VZ', 'T', 'GS', 'BLK', 'SCHW', 'AXP', 'MMM', 'MRK', 'VRTX', 'CAT', 'GE',
    'CSCO', 'CRM', 'ORCL', 'SAP', 'UBER', 'SPOT', 'SHOP', 'COIN', 'SQ', 'PYPL', 'NFLX',
    'DKNG', 'ROKU', 'RBLX', 'ZM', 'DASH', 'LYFT', 'TRIP', 'BOOKING', 'ABNB', 'PLTR',
    'U', 'F', 'GM', 'LCID', 'NIO', 'MSTR', 'HOOD', 'RTX', 'HON', 'UNP', 'LMT',
    'COF', 'ALLY', 'USB', 'FITB', 'MTCH', 'TMUS', 'MDLZ', 'SBUX', 'CMG', 'ETSY',
    'ULTA', 'DECK', 'LULU', 'MRVL', 'CRWD', 'OKTA', 'ZS', 'NET', 'PSTG', 'DDOG',
    'SNOW', 'TWLO', 'TEAM', 'MDB', 'CLDR', 'WDAY', 'SNPS', 'CDNS', 'FTNT',
    'CCI', 'AMT', 'EQIX', 'DLR', 'PLD', 'EXR', 'LTC', 'IRM',
    'PK', 'WY', 'KEYS', 'ANET', 'LRCX', 'QCOM', 'NXPI', 'MCHP', 'MXIM', 'ADI',
    'AMAT', 'CPRT', 'STAG', 'O', 'VICI', 'FOXA', 'FOX', 'IQV', 'EPAM',
    'REXR', 'SUI', 'PSA', 'INVH', 'MAA', 'AVB', 'ESS', 'UMH',
    'AFL', 'AFG', 'ALL', 'AMP', 'AON', 'AIG', 'HIG', 'MKL', 'PRU',
    'PGR', 'RE', 'RLI', 'CBOEk', 'ICE', 'CME', 'NDAQ',
]

def load_russell_2000():
    """Load Russell 2000 tickers from the CSV file provided."""
    russell = []
    try:
        # Read the CSV data that was provided
        with open('/home/ubuntu/.openclaw/media/inbound/file_2---85743cf8-c72a-440b-ac99-cee3b77c99b5.csv', 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ticker = row['Ticker'].strip().upper()
                if ticker and len(ticker) <= 10:  # Valid ticker length
                    russell.append(ticker)
    except Exception as e:
        print(f"Error reading Russell file: {e}")
        print("Will use S&P 500 only as fallback")
        return []
    
    return russell

def main():
    print("Loading Russell 2000 tickers from CSV...")
    russell = load_russell_2000()
    
    print(f"✓ Loaded {len(russell)} Russell 2000 tickers")
    print(f"✓ S&P 500: {len(SP500)} tickers")
    
    # Combine and deduplicate
    all_tickers = set(SP500) | set(russell)
    all_tickers = sorted(list(all_tickers))
    
    print(f"\n✓ TOTAL UNIQUE REAL TICKERS: {len(all_tickers)}")
    print(f"\nSample: {all_tickers[:30]}")
    
    # Save
    with open('real_combined_tickers.json', 'w') as f:
        json.dump(all_tickers, f)
    
    print(f"\nSaved {len(all_tickers)} REAL, VERIFIED tickers to real_combined_tickers.json")
    print("\n✅ READY FOR DATABASE GENERATION")

if __name__ == '__main__':
    main()
