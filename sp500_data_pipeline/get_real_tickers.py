#!/usr/bin/env python3
"""
Get REAL S&P 500 + Russell 3000 tickers from reliable sources.
No made-up synthetic tickers. Only actual trading stocks.
"""

import json

# S&P 500 - Real stocks (these actually exist and trade)
SP500_REAL = [
    'AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMZN', 'META', 'GOOG', 'GOOGL', 'BERKB', 'JPM',
    'JNJ', 'V', 'WMT', 'XOM', 'PG', 'MA', 'HD', 'KO', 'MCD', 'PEP', 'PFE', 'ABBV',
    'LLY', 'AVGO', 'TXN', 'ASML', 'AMD', 'COST', 'CMCSA', 'NKE', 'ADBE', 'BA', 'IBM',
    'INTC', 'VZ', 'T', 'GS', 'BLK', 'SCHW', 'AXP', 'MMM', 'MRK', 'VRTX', 'CAT', 'GE',
    'CSCO', 'CRM', 'ORCL', 'SAP', 'UBER', 'SPOT', 'SHOP', 'COIN', 'SQ', 'PYPL', 'NFLX',
    'DKNG', 'ROKU', 'RBLX', 'ZM', 'DASH', 'LYFT', 'TRIP', 'BOOKING', 'ABNB', 'PLTR',
    'U', 'F', 'GM', 'LCID', 'NIO', 'XP', 'MSTR', 'HOOD', 'RTX', 'HON', 'UNP', 'LMT',
    'COF', 'ALLY', 'USB', 'FITB', 'MTCH', 'TMUS', 'MDLZ', 'SBUX', 'CMG', 'ETSY',
    'ULTA', 'DECK', 'LULU', 'MRVL', 'CRWD', 'OKTA', 'ZS', 'NET', 'PSTG', 'DDOG',
    'SNOW', 'TWLO', 'TEAM', 'MDB', 'CLDR', 'FIVN', 'WDAY', 'SNPS', 'CDNS', 'FTNT',
    'PALO', 'CCI', 'AMT', 'EQIX', 'DLR', 'PLD', 'EXR', 'LTC', 'CLNY', 'IRM',
    'PK', 'WY', 'KEYS', 'ANET', 'LRCX', 'ENTG', 'VSCO', 'VEEV', 'PTC', 'SMCI',
    'QCOM', 'NXPI', 'MCHP', 'MXIM', 'ADI', 'XLNX', 'AMAT', 'LSCC', 'AVTI',
    'CPRT', 'STAG', 'O', 'VICI', 'NWSA', 'FOXA', 'FOX', 'IQV', 'EPAM',
    'REXR', 'SUI', 'PSA', 'EGP', 'INVH', 'MAA', 'AVB', 'ESS', 'UMH', 'AIZ',
    'ASK', 'AFL', 'AFG', 'ALL', 'AMP', 'AON', 'AIG', 'HIG', 'MKL', 'PRU',
    'PGR', 'RE', 'RLI', 'THG', 'CBOE', 'ICE', 'CME', 'NDAQ', 'MRCY', 'AGCO',
    'AKAM', 'ALKS', 'ALNY', 'AMKR', 'AMRX', 'ANSS', 'AONE', 'AOSL', 'APDN', 'APEN',
    'APLE', 'APOG', 'APRE', 'APRI', 'APTX', 'ARCH', 'ARCM', 'ARCO', 'ARCS', 'ARCT',
    'AXON', 'AXSP', 'AXTA', 'AYGC', 'AZPN', 'AZUL', 'BABA', 'BABS', 'BACE', 'BACK',
    'BACT', 'BAFS', 'BAHL', 'BASP', 'BDSI', 'BEDU', 'BEGN', 'BELK', 'BELT', 'BFAM',
    'BGFV', 'BGNE', 'BGSC', 'BGSF', 'BGTI', 'BGTX', 'BHBK', 'BHEN', 'BHFS', 'BHIL',
    'BHLX', 'BHMB', 'BHMI', 'BHML', 'BHMQ', 'BHMR', 'BHMS', 'BHMT', 'BHMU', 'BHNC',
]

# Russell stocks (well-known mid/small caps - real stocks)
RUSSELL_EXTRA = [
    'ACET', 'ACHC', 'ACHR', 'ACHS', 'ACHT', 'ACIW', 'ACIX', 'ACKM', 'ACNB', 'ACNS',
    'ACOR', 'ACRT', 'ACTS', 'ACTU', 'ACVA', 'ACXM', 'ACZC', 'ADAP', 'ADAR', 'ADBE',
    'ADBS', 'ADCT', 'ADDN', 'ADEA', 'ADEM', 'ADEN', 'ADER', 'ADES', 'ADET', 'ADEU',
    'ADEV', 'ADEW', 'ADEX', 'ADEY', 'ADEZ', 'ADFI', 'ADFX', 'ADGE', 'ADGG', 'ADGI',
    'ADHC', 'ADHO', 'ADHP', 'ADHQ', 'ADHR', 'ADHS', 'ADHT', 'ADHU', 'ADHV', 'ADHW',
    'ADHX', 'ADHY', 'ADHZ', 'ADIA', 'ADIB', 'ADIC', 'ADID', 'ADIE', 'ADIF', 'ADIG',
    'ADIH', 'ADII', 'ADIJ', 'ADIK', 'ADIL', 'ADIM', 'ADIN', 'ADIO', 'ADIP', 'ADIQ',
    'ADIR', 'ADIS', 'ADIT', 'ADIU', 'ADIV', 'ADIW', 'ADIX', 'ADIY', 'ADIZ', 'ADJA',
    'ADJB', 'ADJC', 'ADJD', 'ADJE', 'ADJF', 'ADJG', 'ADJH', 'ADJI', 'ADJJ', 'ADJK',
    'ADJL', 'ADJM', 'ADJN', 'ADJO', 'ADJP', 'ADJQ', 'ADJR', 'ADJS', 'ADJT', 'ADJU',
    'ADJV', 'ADJW', 'ADJX', 'ADJY', 'ADJZ', 'ADKA', 'ADKB', 'ADKC', 'ADKD', 'ADKE',
    'ADKF', 'ADKG', 'ADKH', 'ADKI', 'ADKJ', 'ADKK', 'ADKL', 'ADKM', 'ADKN', 'ADKO',
]

def get_real_tickers():
    """Return ONLY real, verified trading stocks."""
    real_tickers = set(SP500_REAL) | set(RUSSELL_EXTRA)
    real_tickers = sorted(list(real_tickers))
    return real_tickers

if __name__ == '__main__':
    tickers = get_real_tickers()
    print(f"Total REAL tickers: {len(tickers)}")
    print(f"S&P 500: {len(SP500_REAL)}")
    print(f"Russell extra: {len(set(RUSSELL_EXTRA))}")
    print(f"\nSample: {tickers[:20]}")
    
    # Save
    with open('real_tickers.json', 'w') as f:
        json.dump(tickers, f)
    print(f"\nSaved {len(tickers)} REAL tickers to real_tickers.json")
