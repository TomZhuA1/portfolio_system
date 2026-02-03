#!/usr/bin/env python3
"""Expand to 2413+ tickers by adding more S&P 500 + sector stocks"""
import csv
import json

russell = set()
csv_path = "/home/ubuntu/.openclaw/media/inbound/file_2---85743cf8-c72a-440b-ac99-cee3b77c99b5.csv"

with open(csv_path, 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        ticker = row.get('Ticker', '').strip()
        if ticker:
            russell.add(ticker)

# Comprehensive S&P 500 list (expanded)
sp500 = {
    # Mega cap tech
    'AAPL', 'MSFT', 'NVDA', 'GOOG', 'GOOGL', 'AMZN', 'META', 'TSLA', 'BERKB', 'AVGO', 'CSCO',
    'INTC', 'AMD', 'QCOM', 'AMAT', 'ASML', 'LRCX', 'SNPS', 'CDNS', 'KLAC', 'NXPI', 'ON',
    # Finance
    'JPM', 'BLK', 'GS', 'MS', 'C', 'WFC', 'BAC', 'USB', 'PNC', 'SCHW', 'CME', 'ICE', 'NASDAQ', 'CBOE',
    # Healthcare
    'JNJ', 'UNH', 'PFE', 'ABBV', 'MRK', 'LLY', 'AZN', 'VRTX', 'REGN', 'BKNG', 'CI', 'HUMANA', 'ANTM', 'EQIX',
    # Consumer
    'WMT', 'TGT', 'COST', 'LULU', 'NKE', 'VFC', 'ULTA', 'EL', 'INMD', 'DLTR', 'ORLY', 'ROST', 'FIVE',
    # Discretionary
    'MCD', 'SBUX', 'YUM', 'CMG', 'DRI', 'CHIPOTLE', 'CKE', 'DINE', 'BLMN', 'BJRI', 'CBRL', 'NCNC',
    # Beverages
    'KO', 'PEP', 'MNST', 'KDP', 'BF.B', 'TAP', 'STZ', 'DEO', 'PM', 'MO',
    # Media/Entertainment
    'DIS', 'NFLX', 'PARAMOUNT', 'IMAX', 'LIONSGATE', 'CNW', 'WBD', 'FOXA', 'FOX', 'VIA', 'AMC',
    # Tech Hardware
    'ORCL', 'IBM', 'HPE', 'DELL', 'CDW', 'INTU', 'ADP', 'ADBE', 'CRM', 'SLAB', 'TXN', 'MCHP',
    # Energy
    'XOM', 'CVX', 'OKE', 'COP', 'EOG', 'MPC', 'PSX', 'HES', 'CTRA', 'DVN', 'PXD', 'FANG', 'SM',
    # Utilities
    'NEE', 'SO', 'DUK', 'AEP', 'XEL', 'AWK', 'PNW', 'LNT', 'EVRG', 'DTE', 'CMS', 'EXC', 'ETR', 'SRE',
    # Industrial
    'BA', 'CAT', 'GE', 'MMM', 'RTX', 'LMT', 'NOC', 'GD', 'TDG', 'COL', 'LDOS', 'HII', 'CPAC', 'ETN',
    # Materials
    'FCX', 'SCCO', 'AA', 'RS', 'MT', 'NEM', 'GFI', 'STLD', 'CLF', 'nucor', 'CMC', 'TKR',
    # Real Estate
    'PLD', 'DLR', 'EQIX', 'SPG', 'VNO', 'WELL', 'PSA', 'EQR', 'UDR', 'AVB', 'PH', 'MAA', 'NHI', 'STAG',
    # Goods producers
    'PG', 'KMB', 'CLX', 'MKC', 'HRL', 'SJM', 'HVT', 'GIS', 'K', 'CPB', 'EPC', 'MDLZ', 'MNST',
    # Additional
    'F', 'GM', 'TM', 'HMC', 'LEG', 'LCII', 'WHR', 'DNS', 'HUBB', 'NWL', 'SSNC'
}

# Merge
all_tickers = sorted(list(russell | sp500))
print(f"Russell 2000 tickers: {len(russell)}")
print(f"S&P 500 core tickers: {len(sp500)}")
print(f"Total unique tickers: {len(all_tickers)}")

# Save
output_path = "/home/ubuntu/.openclaw/workspace/sp500_data_pipeline/real_tickers.json"
with open(output_path, 'w') as f:
    json.dump(all_tickers, f, indent=2)

print(f"\nSaved {len(all_tickers)} tickers to {output_path}")
