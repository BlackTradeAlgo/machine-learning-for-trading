#!/usr/bin/env python3
"""
Sirf Near Expiry Dikhao - Angel One se direct
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
import pandas as pd
from datetime import date

load_dotenv()

from core.market_data.angel_one_api import AngelOneAPI

api_key = os.getenv('ANGEL_API_KEY')
client_id = os.getenv('ANGEL_CLIENT_ID')
password = os.getenv('ANGEL_PASSWORD')
totp_secret = os.getenv('ANGEL_TOTP_SECRET')

print("\n" + "="*80)
print("ANGEL ONE - NEAR EXPIRY CHECK")
print("="*80)

print("\nConnecting...")
api = AngelOneAPI(api_key, client_id, password, totp_secret)
api.login()

print(f"✓ Total instruments: {len(api.instrument_master):,}")

symbols = ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'SENSEX', 'MIDCPNIFTY']

print("\n" + "="*80)
print("NEAR EXPIRY - DIRECT FROM ANGEL ONE")
print("="*80)

for symbol in symbols:
    print(f"\n{symbol}:")

    # Get options for this symbol
    opts = api.instrument_master[
        (api.instrument_master['name'] == symbol) &
        (api.instrument_master['instrumenttype'].isin(['OPTIDX', 'OPTSTK']))
    ]

    if opts.empty:
        print("  No data")
        continue

    # Get unique expiries (raw)
    expiries = opts['expiry'].unique()

    print(f"  Total options: {len(opts)}")
    print(f"  Unique expiries found: {len(expiries)}")
    print(f"\n  First 10 expiries (raw):")

    for i, exp in enumerate(sorted(expiries)[:10], 1):
        print(f"    {i}. {exp}")

api.logout()

print("\n" + "="*80)
print("✅ DONE - Check karo yeh expiries sahi hain ya nahi")
print("="*80 + "\n")
