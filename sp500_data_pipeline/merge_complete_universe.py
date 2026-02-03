#!/usr/bin/env python3
"""
Merge S&P 500 (with sectors) + Russell 2000 CSV into complete 2413+ ticker universe
with sector mapping.
"""
import csv
import json

# Load S&P 500 with sectors
sp500 = {}
with open('/tmp/sp500_data.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        ticker = row['Symbol'].strip()
        sector = row['Sector'].strip()
        if ticker:
            sp500[ticker] = sector

print(f"✓ Loaded {len(sp500)} S&P 500 tickers with sectors")

# Load Russell 2000 (assign to 'Small Cap' sector since not provided)
russell = {}
with open('/home/ubuntu/.openclaw/media/inbound/file_2---85743cf8-c72a-440b-ac99-cee3b77c99b5.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        ticker = row['Ticker'].strip()
        if ticker and ticker not in sp500:  # Avoid duplicates
            russell[ticker] = 'Small Cap'  # Default sector for Russell 2000

print(f"✓ Loaded {len(russell)} Russell 2000 tickers (excluding S&P 500 overlaps)")

# Merge
merged = {**sp500, **russell}
tickers_only = sorted(list(merged.keys()))

print(f"\n✓ TOTAL UNIQUE TICKERS: {len(merged)}")
print(f"  - S&P 500: {len(sp500)}")
print(f"  - Russell 2000 (net): {len(russell)}")
print(f"  - Combined: {len(merged)}")

# Save tickers only (for data generation)
with open('/home/ubuntu/.openclaw/workspace/sp500_data_pipeline/real_tickers.json', 'w') as f:
    json.dump(tickers_only, f, indent=2)
print(f"\n✓ Saved {len(tickers_only)} tickers to real_tickers.json")

# Save with sectors (for scoring system)
with open('/home/ubuntu/.openclaw/workspace/sp500_data_pipeline/ticker_sectors.json', 'w') as f:
    json.dump(merged, f, indent=2)
print(f"✓ Saved {len(merged)} tickers with sectors to ticker_sectors.json")

print(f"\nSample tickers (first 20):\n  {tickers_only[:20]}")
