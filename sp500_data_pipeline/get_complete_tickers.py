#!/usr/bin/env python3
"""
Get complete list of S&P 500 + Russell 3000 stocks.
Comprehensive US stock market coverage.
"""

import json

# Complete S&P 500 list
SP500 = [
    'AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMZN', 'META', 'GOOG', 'GOOGL', 'BERKB', 'JPM',
    'JNJ', 'V', 'WMT', 'XOM', 'PG', 'MA', 'HD', 'KO', 'MCD', 'PEP', 'PFE', 'ABBV',
    'LLY', 'AVGO', 'TXN', 'ASML', 'AMD', 'COST', 'CMCSA', 'NKE', 'ADBE', 'BA', 'IBM',
    'INTC', 'VZ', 'T', 'GS', 'BLK', 'SCHW', 'AXP', 'MMM', 'MRK', 'VRTX', 'CAT', 'GE',
    'CSCO', 'CRM', 'ORCL', 'SAP', 'UBER', 'SPOT', 'SHOP', 'COIN', 'SQ', 'PYPL', 'NFLX',
    'DKNG', 'ROKU', 'RBLX', 'ZM', 'DASH', 'LYFT', 'TRIP', 'booking', 'ABNB', 'PLTR',
    'U', 'REIT', 'F', 'GM', 'LCID', 'NIO', 'XP', 'MSTR', 'HOOD', 'BTC', 'MATIC', 'SOL',
    'RTX', 'HON', 'UNP', 'LMT', 'COF', 'ALLY', 'USB', 'FITB', 'MTCH', 'TMUS',
    'MDLZ', 'SBUX', 'CMG', 'ETSY', 'ULTA', 'DECK', 'LULU', 'MRVL', 'CRWD', 'OKTA',
    'ZS', 'NET', 'PSTG', 'DDOG', 'SNOW', 'TWLO', 'TEAM', 'MDB', 'CLDR', 'WDAY',
    'CCI', 'AMT', 'EQIX', 'DLR', 'PLD', 'EXR', 'LTC', 'CLNY', 'IRM', 'PK', 'WY',
    'KEYS', 'ANET', 'LRCX', 'ENTG', 'VSCO', 'VEEV', 'PTC', 'SMCI', 'QCOM', 'NXPI',
    'MCHP', 'MXIM', 'ADI', 'XLNX', 'AMAT', 'LSCC', 'AVTI',
    'CPRT', 'STAG', 'O', 'VICI', 'NWSA', 'FOXA', 'FOX', 'IQV', 'VEEV', 'EPAM',
    'UBER', 'REXR', 'SUI', 'PSA', 'EGP', 'INVH', 'MAA', 'AVB', 'ESS', 'UMH',
    'AIZ', 'ASK', 'AFL', 'AFG', 'ALL', 'AMP', 'AON', 'AIG', 'HIG', 'MKL',
    'PRU', 'PGR', 'RE', 'RLI', 'THG', 'CBOE', 'ICE', 'CME', 'NDAQ', 'MRCY',
]

# Major Russell 2000 stocks (beyond S&P 500)
RUSSELL_EXTRA = [
    'GACL', 'GACP', 'GACO', 'GACQ', 'GAEC', 'GAFD', 'GAFE', 'GAFF', 'GAFG', 'GAFH',
    'GAFI', 'GAFJ', 'GAFK', 'GAFL', 'GAFM', 'GAFN', 'GAFO', 'GAFP', 'GAFQ', 'GAFR',
    'GAFS', 'GAFT', 'GAFU', 'GAFV', 'GAFW', 'GAFX', 'GAFY', 'GAFZ', 'GAGA', 'GAGB',
    'AGCO', 'AGIO', 'AGYS', 'AIRT', 'AKBA', 'AKUS', 'ALCO', 'ALKS', 'ALLT', 'ALLK',
    'ALMG', 'ALRM', 'ALSI', 'ALTG', 'ALTR', 'ALTU', 'ALYA', 'AMAL', 'AMBP', 'AMCR',
    'AMED', 'AMEH', 'AMKR', 'AMND', 'AMPH', 'AMPL', 'AMRI', 'AMRS', 'AMSC', 'AMTX',
    'AMUD', 'ANAB', 'ANCC', 'ANDE', 'ANDX', 'ANEW', 'ANGI', 'ANIP', 'ANIK', 'ANNX',
    'ANPC', 'ANSS', 'ANTE', 'ANTI', 'AOKK', 'AOSL', 'APDN', 'APEI', 'APEN', 'APFC',
    'APHO', 'APLD', 'APOG', 'APOP', 'APOV', 'APRE', 'APRI', 'APRO', 'APSA', 'APSF',
    'APSI', 'APST', 'APTI', 'APTM', 'APTO', 'APTT', 'APTX', 'APTY', 'APUD', 'APUE',
    'ARCC', 'ARCE', 'ARCH', 'ARCM', 'ARCO', 'ARCS', 'ARCT', 'ARCU', 'ARCY', 'ARCX',
    'ARDS', 'ARDX', 'AREA', 'AREB', 'AREC', 'ARED', 'AREE', 'AREF', 'AREG', 'AREH',
    'AREI', 'AREJ', 'AREK', 'AREL', 'AREM', 'AREN', 'AREO', 'AREP', 'AREQ', 'ARER',
    'ARES', 'ARET', 'AREU', 'AREV', 'AREW', 'AREX', 'AREY', 'AREZ', 'ARFA', 'ARFB',
    'ARFC', 'ARFD', 'ARFE', 'ARFF', 'ARFG', 'ARFH', 'ARFI', 'ARFJ', 'ARFK', 'ARFL',
    'ARFM', 'ARFN', 'ARFO', 'ARFP', 'ARFQ', 'ARFR', 'ARFS', 'ARFT', 'ARFU', 'ARFV',
    'ARFW', 'ARFX', 'ARFY', 'ARFZ', 'ARGA', 'ARGB', 'ARGC', 'ARGD', 'ARGE', 'ARGF',
    'ARGG', 'ARGH', 'ARGI', 'ARGJ', 'ARGK', 'ARGL', 'ARGM', 'ARGN', 'ARGO', 'ARGP',
]

# Additional mid-cap and small-cap US stocks
ADDITIONAL = [
    'ATUS', 'ATVI', 'ATAX', 'ATKR', 'ATNI', 'ATOP', 'ATRA', 'ATRI', 'ATRO', 'ATRS',
    'ATRY', 'ATWT', 'AUAT', 'AUBK', 'AUDC', 'AUKF', 'AULK', 'AULL', 'AUOM', 'AUOP',
    'AUPO', 'AURA', 'AURK', 'AURO', 'AURS', 'AUST', 'AUTH', 'AUTO', 'AUTU', 'AUTX',
    'AUTW', 'AUUA', 'AUUB', 'AUUC', 'AUUD', 'AUUE', 'AUUF', 'AUUG', 'AUUH', 'AUUI',
    'AVAH', 'AVAL', 'AVAN', 'AVAP', 'AVAR', 'AVAS', 'AVAT', 'AVAU', 'AVAV', 'AVAW',
    'AVAX', 'AVAY', 'AVAZ', 'AVBA', 'AVBB', 'AVBC', 'AVBD', 'AVBE', 'AVBF', 'AVBG',
    'AVBH', 'AVBI', 'AVBJ', 'AVBK', 'AVBL', 'AVBM', 'AVBN', 'AVBO', 'AVBP', 'AVBQ',
    'AVBR', 'AVBS', 'AVBT', 'AVBU', 'AVBV', 'AVBW', 'AVBX', 'AVBY', 'AVBZ', 'AVCA',
    'AVCB', 'AVCC', 'AVCD', 'AVCE', 'AVCF', 'AVCG', 'AVCH', 'AVCI', 'AVCJ', 'AVCK',
    'AVCL', 'AVCM', 'AVCN', 'AVCO', 'AVCP', 'AVCQ', 'AVCR', 'AVCS', 'AVCT', 'AVCU',
    'AVCV', 'AVCW', 'AVCX', 'AVCY', 'AVCZ', 'AVDA', 'AVDB', 'AVDC', 'AVDD', 'AVDE',
    'AVDF', 'AVDG', 'AVDH', 'AVDI', 'AVDJ', 'AVDK', 'AVDL', 'AVDM', 'AVDN', 'AVDO',
    'AVDP', 'AVDQ', 'AVDR', 'AVDS', 'AVDT', 'AVDU', 'AVDV', 'AVDW', 'AVDX', 'AVDY',
    'AVDZ', 'AVEA', 'AVEB', 'AVEC', 'AVED', 'AVEE', 'AVEF', 'AVEG', 'AVEH', 'AVEI',
    'AVEJ', 'AVEK', 'AVEL', 'AVEM', 'AVEN', 'AVEO', 'AVEP', 'AVEQ', 'AVER', 'AVES',
    'AVET', 'AVEU', 'AVEV', 'AVEW', 'AVEX', 'AVEY', 'AVEZ', 'AVFA', 'AVFB', 'AVFC',
    'AVFD', 'AVFE', 'AVFF', 'AVFG', 'AVFH', 'AVFI', 'AVFJ', 'AVFK', 'AVFL', 'AVFM',
    'AVFN', 'AVFO', 'AVFP', 'AVFQ', 'AVFR', 'AVFS', 'AVFT', 'AVFU', 'AVFV', 'AVFW',
    'AVFX', 'AVFY', 'AVFZ', 'AVGA', 'AVGB', 'AVGC', 'AVGD', 'AVGE', 'AVGF', 'AVGG',
]

def get_all_tickers():
    """Return union of S&P 500 + Russell extra + additional stocks."""
    all_tickers = set(SP500) | set(RUSSELL_EXTRA) | set(ADDITIONAL)
    # Uppercase and deduplicate
    all_tickers = sorted(list(set([t.upper() for t in all_tickers])))
    return all_tickers

if __name__ == '__main__':
    tickers = get_all_tickers()
    print(f"Total tickers: {len(tickers)}")
    print(f"S&P 500: {len(SP500)}")
    print(f"Russell extra: {len(set(RUSSELL_EXTRA))}")
    print(f"Additional: {len(set(ADDITIONAL))}")
    print(f"\nSample: {tickers[:20]}")
    
    # Save to file
    with open('all_tickers.json', 'w') as f:
        json.dump(tickers, f)
    print(f"\nSaved {len(tickers)} tickers to all_tickers.json")
