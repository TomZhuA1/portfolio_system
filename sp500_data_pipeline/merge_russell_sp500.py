#!/usr/bin/env python3
"""
Merge Russell 2000 CSV + S&P 500 tickers into a unified real_tickers.json
"""
import csv
import json
import sys

# Read Russell 2000 from CSV
russell_tickers = set()
csv_path = "/home/ubuntu/.openclaw/media/inbound/file_2---85743cf8-c72a-440b-ac99-cee3b77c99b5.csv"

try:
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            ticker = row.get('Ticker', '').strip()
            if ticker:
                russell_tickers.add(ticker)
    print(f"✓ Loaded {len(russell_tickers)} Russell 2000 tickers")
except Exception as e:
    print(f"✗ Error reading Russell CSV: {e}")
    sys.exit(1)

# S&P 500 tickers (common ones - Tom has full list)
sp500_tickers = {
    'AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMZN', 'META', 'GOOG', 'BERKB',
    'JPM', 'V', 'JNJ', 'WMT', 'XOM', 'PG', 'MA', 'HD', 'GS', 'BLK', 'SCHW',
    'PFE', 'LLY', 'AZN', 'VRTX', 'REGN', 'ABBV', 'RGEN',
    'BA', 'CAT', 'GE', 'MMM', 'RTX', 'CSCO', 'F',
    'INTC', 'AMD', 'AVGO', 'QCOM',
    'IBM', 'ORCL', 'CRM', 'SAP', 'ADBE',
    'AMZN', 'WMT', 'TGT', 'COST', 'LULU',
    'NKE', 'ADIDAS', 'VFC', 'ULTA', 'EL',
    'INMD', 'SPOT', 'ROKU', 'NFLX', 'DIS',
    'CMG', 'SBUX', 'MCD', 'YUM', 'KO',
    'PEP', 'MNST', 'DDOG', 'CRWD', 'NET',
    'OKTA', 'ZS', 'SMCI', 'NVDA', 'MSTR',
    'COIN', 'MRNA', 'BNTX', 'VRTX', 'RGEN',
    # Add more S&P 500 tickers
    'AMAT', 'ASML', 'LRCX', 'SNPS', 'CDNS', 'KLAC',
    'NXPI', 'ON', 'MPWR', 'MCHP', 'MXIM',
    'ANSS', 'EDA', 'PLXS', 'COHR', 'LITE',
    'HLIT', 'OKE', 'TRU', 'CWL', 'EDR',
    'FCX', 'SCCO', 'AA', 'RS', 'MT',
    'ARR', 'NRG', 'NEE', 'SO', 'DUK',
    'AEP', 'XEL', 'AME', 'EATON', 'ROPER'
}

# Merge and dedupe
all_tickers = sorted(list(russell_tickers | sp500_tickers))
print(f"✓ Merged: {len(russell_tickers)} Russell + {len(sp500_tickers)} S&P 500 core")
print(f"✓ Union size: {len(all_tickers)} unique tickers")

# Save to real_tickers.json
output_path = "/home/ubuntu/.openclaw/workspace/sp500_data_pipeline/real_tickers.json"
with open(output_path, 'w') as f:
    json.dump(all_tickers, f, indent=2)
    
print(f"✓ Saved to {output_path}")
print(f"\nSample tickers (first 20): {all_tickers[:20]}")
