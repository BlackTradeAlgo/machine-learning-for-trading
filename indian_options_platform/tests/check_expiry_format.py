#!/usr/bin/env python3
"""
Check Expiry Format in Angel One Data
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
import pandas as pd

load_dotenv()

from core.market_data.angel_one_api import AngelOneAPI

def check_expiry_format():
    """Check the actual expiry format in Angel One data"""

    print("\n" + "="*80)
    print("CHECKING EXPIRY FORMAT IN ANGEL ONE DATA")
    print("="*80)

    # Load credentials
    api_key = os.getenv('ANGEL_API_KEY')
    client_id = os.getenv('ANGEL_CLIENT_ID')
    password = os.getenv('ANGEL_PASSWORD')
    totp_secret = os.getenv('ANGEL_TOTP_SECRET')

    print("\nConnecting to Angel One...")
    api = AngelOneAPI(api_key, client_id, password, totp_secret)

    if not api.login():
        print("❌ Login failed")
        return

    print("✅ Connected")

    # Check NIFTY options
    nifty_options = api.instrument_master[
        (api.instrument_master['name'] == 'NIFTY') &
        (api.instrument_master['instrumenttype'].isin(['OPTIDX', 'OPTSTK']))
    ].copy()

    print(f"\n✓ Found {len(nifty_options)} NIFTY options")

    # Show sample records
    print("\nSample NIFTY Options (First 10 records):")
    print("="*80)

    cols_to_show = ['symbol', 'name', 'expiry', 'strike', 'instrumenttype', 'exch_seg']

    for idx, row in nifty_options.head(10).iterrows():
        print(f"\nRecord {idx}:")
        for col in cols_to_show:
            if col in row:
                print(f"  {col}: {row[col]}")

    # Check unique expiry values
    print("\n" + "="*80)
    print("UNIQUE EXPIRY VALUES (First 20):")
    print("="*80)

    unique_expiries = nifty_options['expiry'].unique()[:20]
    print(f"\nTotal unique expiries: {len(nifty_options['expiry'].unique())}")
    print("\nFirst 20 expiries:")
    for i, exp in enumerate(unique_expiries, 1):
        print(f"{i}. {exp}")

    # Try to parse expiries
    print("\n" + "="*80)
    print("PARSING EXPIRIES:")
    print("="*80)

    print("\nTrying different date formats...")

    # Format 1: DD MMM YYYY
    print("\n1. Format: DD MMM YYYY (e.g., '07NOV2024')")
    nifty_options['exp_parsed_1'] = pd.to_datetime(nifty_options['expiry'], format='%d%b%Y', errors='coerce')
    parsed_1 = nifty_options['exp_parsed_1'].notna().sum()
    print(f"   Parsed: {parsed_1} / {len(nifty_options)}")

    # Format 2: DD MMM YY
    print("\n2. Format: DD MMM YY (e.g., '07NOV24')")
    nifty_options['exp_parsed_2'] = pd.to_datetime(nifty_options['expiry'], format='%d%b%y', errors='coerce')
    parsed_2 = nifty_options['exp_parsed_2'].notna().sum()
    print(f"   Parsed: {parsed_2} / {len(nifty_options)}")

    # Format 3: YYYY-MM-DD
    print("\n3. Format: YYYY-MM-DD")
    nifty_options['exp_parsed_3'] = pd.to_datetime(nifty_options['expiry'], format='%Y-%m-%d', errors='coerce')
    parsed_3 = nifty_options['exp_parsed_3'].notna().sum()
    print(f"   Parsed: {parsed_3} / {len(nifty_options)}")

    # Format 4: Auto-detect
    print("\n4. Format: Auto-detect")
    nifty_options['exp_parsed_4'] = pd.to_datetime(nifty_options['expiry'], errors='coerce')
    parsed_4 = nifty_options['exp_parsed_4'].notna().sum()
    print(f"   Parsed: {parsed_4} / {len(nifty_options)}")

    # Show parsed dates
    best_format = max([(parsed_1, 'DD%b%Y'), (parsed_2, '%d%b%y'), (parsed_3, '%Y-%m-%d'), (parsed_4, 'auto')], key=lambda x: x[0])

    print(f"\n✓ Best format: {best_format[1]} ({best_format[0]} parsed)")

    if best_format[0] > 0:
        if best_format[1] == 'auto':
            nifty_options['parsed_date'] = pd.to_datetime(nifty_options['expiry'], errors='coerce').dt.date
        else:
            nifty_options['parsed_date'] = pd.to_datetime(nifty_options['expiry'], format=best_format[1], errors='coerce').dt.date

        # Show next 10 expiries
        future_expiries = nifty_options[nifty_options['parsed_date'].notna()].copy()
        future_expiries = future_expiries.sort_values('parsed_date')

        print("\nNext 10 NIFTY Expiries (Parsed):")
        print("="*80)

        for idx, row in future_expiries.head(10).iterrows():
            print(f"{row['symbol']}: {row['expiry']} → {row['parsed_date']}")

    api.logout()
    print("\n✅ Check complete\n")


if __name__ == '__main__':
    check_expiry_format()
