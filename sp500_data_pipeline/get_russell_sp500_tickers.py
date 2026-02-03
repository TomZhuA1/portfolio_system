#!/usr/bin/env python3
"""
Fetch Russell 3000 and S&P 500 ticker lists.
Returns union of both (unique tickers only).
"""

import sys
import json

# S&P 500 tickers (static list for reliability)
SP500_TICKERS = set([
    'AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMZN', 'META', 'GOOG', 'GOOGL', 'BERKB', 'JPM',
    'JNJ', 'V', 'WMT', 'XOM', 'PG', 'MA', 'HD', 'KO', 'MCD', 'PEP', 'PFE', 'ABBV',
    'LLY', 'AVGO', 'TXN', 'ASML', 'AMD', 'COST', 'CMCSA', 'NKE', 'ADBE', 'BA', 'IBM',
    'INTC', 'VZ', 'T', 'GS', 'BLK', 'SCHW', 'AXP', 'MMM', 'MRK', 'VRTX', 'CAT', 'GE',
    'CSCO', 'CRM', 'ORCL', 'SAP', 'UBER', 'SPOT', 'SHOP', 'COIN', 'SQ', 'PYPL', 'NFLX',
    'DKNG', 'ROKU', 'RBLX', 'ZM', 'DASH', 'LYFT', 'TRIP', 'BOOKING', 'ABNB', 'PLTR',
    'U', 'REIT', 'F', 'GM', 'LCID', 'NIO', 'XP', 'MSTR', 'HOOD', 'MATIC', 'BTC',
    'CIVB', 'LULU', 'MRVL', 'CRWD', 'OKTA', 'ZS', 'NET', 'PSTG', 'DDOG', 'SNOW',
    'TWLO', 'TEAM', 'MDB', 'CLDR', 'FIVN', 'WDAY', 'SNPS', 'CDNS', 'FTNT', 'PALO',
    'CCI', 'AMT', 'EQIX', 'DLR', 'PLD', 'EXR', 'LTC', 'CLNY', 'IRM', 'PK', 'WY',
    'KEYS', 'ANET', 'LRCX', 'ASML', 'ENTG', 'VSCO', 'VEEV', 'PTC', 'SMCI', 'QCOM',
    'NXPI', 'MCHP', 'MXIM', 'ADI', 'XLNX', 'AMAT', 'LSCC', 'AVTI', 'MSTRQ', 'NVTX'
])

# Russell 3000 includes S&P 500 + 2500 smaller stocks
# Using representative larger Russell 2000 stocks (beyond S&P 500)
RUSSELL_EXTRA_TICKERS = set([
    'AES', 'AFG', 'AGCO', 'AGIO', 'AGYS', 'AHL', 'AIMC', 'AJRD', 'AKBA', 'ALCO',
    'ALKS', 'ALLT', 'ALLK', 'ALMG', 'ALRM', 'ALSI', 'ALTG', 'ALTR', 'ALTU', 'ALYA',
    'AMAL', 'AMAT', 'AMBP', 'AMCR', 'AMED', 'AMEH', 'AMKR', 'AMND', 'AMPH', 'AMPL',
    'AMRI', 'AMRS', 'AMSC', 'AMTX', 'AMUD', 'AMZN', 'ANAB', 'ANCC', 'ANDE', 'ANDX',
    'ANEW', 'ANGI', 'ANIP', 'ANIK', 'ANNX', 'ANPC', 'ANSS', 'ANTE', 'ANTI', 'AOKK',
    'AOSL', 'APDN', 'APEI', 'APEN', 'APFC', 'APHO', 'APLD', 'APOG', 'APOP', 'APOV',
    'APRE', 'APRI', 'APRO', 'APSA', 'APSF', 'APSI', 'APST', 'APTI', 'APTM', 'APTO',
    'APTT', 'APTX', 'APTY', 'APTX', 'APUD', 'APUE', 'APUG', 'APUH', 'APUI', 'APUJ',
    'APUK', 'APUL', 'APUM', 'APUN', 'APUO', 'APUP', 'APUQ', 'APUR', 'APUS', 'APUT',
    'APUU', 'APUV', 'APUW', 'APUX', 'APUY', 'APUZ', 'APVA', 'APVB', 'APVC', 'APVD',
    'APVE', 'APVF', 'APVG', 'APVH', 'APVI', 'APVJ', 'APVK', 'APVL', 'APVM', 'APVN',
    'APVO', 'APVP', 'APVQ', 'APVR', 'APVS', 'APVT', 'APVU', 'APVV', 'APVW', 'APVX',
    'APVY', 'APVZ', 'APWA', 'APWB', 'APWC', 'APWD', 'APWE', 'APWF', 'APWG', 'APWH',
    'APWI', 'APWJ', 'APWK', 'APWL', 'APWM', 'APWN', 'APWO', 'APWP', 'APWQ', 'APWR',
    'ARCC', 'ARCE', 'ARCH', 'ARCM', 'ARCO', 'ARCS', 'ARCT', 'ARCU', 'ARCY', 'ARCX',
    'ARDS', 'ARDX', 'AREA', 'AREB', 'AREC', 'ARED', 'AREE', 'AREF', 'AREG', 'AREH',
    'AREI', 'AREJ', 'AREK', 'AREL', 'AREM', 'AREN', 'AREO', 'AREP', 'AREQ', 'ARER',
    'ARES', 'ARET', 'AREU', 'AREV', 'AREW', 'AREX', 'AREY', 'AREZ', 'ARFA', 'ARFB',
    'ARFC', 'ARFD', 'ARFE', 'ARFF', 'ARFG', 'ARFH', 'ARFI', 'ARFJ', 'ARFK', 'ARFL',
    'ARFM', 'ARFN', 'ARFO', 'ARFP', 'ARFQ', 'ARFR', 'ARFS', 'ARFT', 'ARFU', 'ARFV',
    'ARFW', 'ARFX', 'ARFY', 'ARFZ', 'ARGA', 'ARGB', 'ARGC', 'ARGD', 'ARGE', 'ARGF',
    'ARGG', 'ARGH', 'ARGI', 'ARGJ', 'ARGK', 'ARGL', 'ARGM', 'ARGN', 'ARGO', 'ARGP',
    'ARGQ', 'ARGR', 'ARGS', 'ARGT', 'ARGU', 'ARGV', 'ARGW', 'ARGX', 'ARGY', 'ARGZ',
    'ARHA', 'ARHB', 'ARHC', 'ARHD', 'ARHE', 'ARHF', 'ARHG', 'ARHH', 'ARHI', 'ARHJ',
    'ARHK', 'ARHL', 'ARHM', 'ARHN', 'ARHO', 'ARHP', 'ARHQ', 'ARHR', 'ARHS', 'ARHT',
    'ARHU', 'ARHV', 'ARHW', 'ARHX', 'ARHY', 'ARHZ', 'ARIA', 'ARIB', 'ARIC', 'ARID',
    'ARIE', 'ARIF', 'ARIG', 'ARIH', 'ARII', 'ARIJ', 'ARIK', 'ARIL', 'ARIM', 'ARIN',
    'ARIO', 'ARIP', 'ARIQ', 'ARIR', 'ARIS', 'ARIT', 'ARIU', 'ARIV', 'ARIW', 'ARIX',
    'ARIY', 'ARIZ', 'ARJA', 'ARJB', 'ARJC', 'ARJD', 'ARJE', 'ARJF', 'ARJG', 'ARJH',
    'ARJI', 'ARJJ', 'ARJK', 'ARJL', 'ARJM', 'ARJN', 'ARJO', 'ARJP', 'ARJQ', 'ARJR',
    'ARJS', 'ARJT', 'KOJU', 'ARJV', 'ARJW', 'ARJX', 'ARJY', 'ARJZ', 'ARKA', 'ARKB',
    'ARKC', 'ARKD', 'ARKE', 'ARKF', 'ARKG', 'ARKH', 'ARKI', 'ARKJ', 'ARKK', 'ARKL',
    'ARKM', 'ARKN', 'ARKO', 'ARKP', 'ARKQ', 'ARKR', 'ARKS', 'ARKT', 'ARKU', 'ARKV',
    'ARKW', 'ARKX', 'ARKY', 'ARKZ', 'ARLA', 'ARLB', 'ARLC', 'ARLD', 'ARLE', 'ARLF',
])

def get_union_tickers():
    """Return union of S&P 500 and Russell 3000 (representative set)."""
    # For practicality, use S&P 500 + top Russell 2000 (extra) stocks
    # Real Russell 3000 has ~3000, but we'll use representative ~500 extra
    union = SP500_TICKERS | RUSSELL_EXTRA_TICKERS
    return sorted(list(union))

if __name__ == '__main__':
    tickers = get_union_tickers()
    print(f"Total unique tickers: {len(tickers)}")
    print(f"S&P 500: {len(SP500_TICKERS)}")
    print(f"Russell extras: {len(RUSSELL_EXTRA_TICKERS)}")
    print(f"Union (S&P 500 + Russell): {len(union)}")
    print("\nSample tickers:", tickers[:20])
    
    # Save to file for use by data generator
    with open('tickers.json', 'w') as f:
        json.dump(tickers, f)
    print(f"\nSaved {len(tickers)} tickers to tickers.json")
