#!/usr/bin/env python3
"""
Find Actual Expiries from Angel One Data
Automatically detects correct expiry days by checking real options data
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
from datetime import date, datetime, timedelta
from collections import defaultdict
import pandas as pd

# Load credentials
load_dotenv()

from core.market_data.angel_one_api import AngelOneAPI

def get_day_name(weekday):
    """Convert weekday number to name"""
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    return days[weekday]


def find_nearest_expiries():
    """Find nearest expiries for all major indices from Angel One data"""

    print("\n" + "="*80)
    print("FINDING ACTUAL EXPIRIES FROM ANGEL ONE DATA")
    print("="*80)

    # Load credentials
    api_key = os.getenv('ANGEL_API_KEY')
    client_id = os.getenv('ANGEL_CLIENT_ID')
    password = os.getenv('ANGEL_PASSWORD')
    totp_secret = os.getenv('ANGEL_TOTP_SECRET')

    if not all([api_key, client_id, password, totp_secret]):
        print("❌ Missing credentials")
        return

    print("\n[1] Connecting to Angel One...")
    api = AngelOneAPI(api_key, client_id, password, totp_secret)

    if not api.login():
        print("❌ Login failed")
        return

    print("✅ Connected successfully")
    print(f"📊 Total instruments: {len(api.instrument_master):,}")

    # Symbols to check
    symbols = ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'SENSEX', 'MIDCPNIFTY']

    print("\n" + "="*80)
    print("[2] FINDING NEAREST EXPIRIES")
    print("="*80)

    today = date.today()
    print(f"\n📅 Today: {today.strftime('%d %B %Y, %A')}")

    results = {}

    for symbol in symbols:
        print(f"\n{'='*80}")
        print(f"Analyzing: {symbol}")
        print('='*80)

        # Filter options for this symbol
        options = api.instrument_master[
            (api.instrument_master['name'] == symbol) &
            (api.instrument_master['instrumenttype'].isin(['OPTIDX', 'OPTSTK']))
        ].copy()

        if options.empty:
            print(f"  ⚠️  No options found for {symbol}")
            continue

        print(f"  ✓ Found {len(options):,} options")

        # Convert expiry to datetime
        options['expiry_date'] = pd.to_datetime(options['expiry'], format='%d%b%y', errors='coerce')

        # Remove invalid dates
        options = options[options['expiry_date'].notna()]

        # Filter future expiries only (convert today to datetime for comparison)
        today_dt = pd.Timestamp(today)
        options = options[options['expiry_date'] >= today_dt]

        # Convert to date for display
        options['expiry_date'] = options['expiry_date'].dt.date

        if options.empty:
            print(f"  ⚠️  No future expiries found")
            continue

        # Get unique expiry dates
        expiries = sorted(options['expiry_date'].unique())

        print(f"  ✓ Found {len(expiries)} future expiry dates")
        print(f"\n  Next 5 Expiries:")
        print(f"  {'#':<5} {'Date':<15} {'Weekday':<15} {'Days Away':<10}")
        print(f"  {'-'*50}")

        for i, exp_date in enumerate(expiries[:5], 1):
            weekday = exp_date.weekday()
            day_name = get_day_name(weekday)
            days_away = (exp_date - today).days

            print(f"  {i:<5} {exp_date.strftime('%d %b %Y'):<15} {day_name:<15} {days_away:<10}")

            # Store first expiry info
            if i == 1:
                results[symbol] = {
                    'date': exp_date,
                    'weekday': weekday,
                    'day_name': day_name,
                    'days_away': days_away,
                    'total_expiries': len(expiries)
                }

        # Analyze expiry pattern (weekly)
        if len(expiries) >= 4:
            print(f"\n  Expiry Pattern Analysis:")
            weekday_counts = defaultdict(int)

            for exp in expiries[:8]:  # Check first 8 expiries
                weekday_counts[exp.weekday()] += 1

            print(f"  Weekday distribution (first 8 expiries):")
            for wd, count in sorted(weekday_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"    {get_day_name(wd)}: {count} times")

    # Summary
    print("\n" + "="*80)
    print("NEAREST EXPIRY SUMMARY")
    print("="*80)

    print(f"\n{'Symbol':<15} {'Nearest Expiry':<15} {'Weekday':<15} {'Days':<10} {'Weekday#':<10}")
    print("-" * 80)

    for symbol, info in results.items():
        print(f"{symbol:<15} {info['date'].strftime('%d %b %Y'):<15} {info['day_name']:<15} {info['days_away']:<10} {info['weekday']:<10}")

    # Generate corrected EXPIRY_DAYS mapping
    print("\n" + "="*80)
    print("RECOMMENDED EXPIRY_DAYS MAPPING")
    print("="*80)

    print("\nEXPIRY_DAYS = {")
    for symbol, info in results.items():
        print(f"    '{symbol}': {info['weekday']},  # {info['day_name']}")
    print("}")

    # Verify against current configuration
    print("\n" + "="*80)
    print("VERIFICATION AGAINST CURRENT CONFIG")
    print("="*80)

    from core.market_data.nse_expiry_engine import NSEExpiryEngine
    engine = NSEExpiryEngine()

    print(f"\n{'Symbol':<15} {'Current':<15} {'Should Be':<15} {'Status':<10}")
    print("-" * 80)

    all_correct = True
    for symbol, info in results.items():
        if symbol in engine.EXPIRY_DAYS:
            current = engine.EXPIRY_DAYS[symbol]
            current_day = get_day_name(current)
            correct_day = info['day_name']

            is_correct = current == info['weekday']
            status = "✅ OK" if is_correct else "❌ WRONG"

            if not is_correct:
                all_correct = False

            print(f"{symbol:<15} {current_day:<15} {correct_day:<15} {status:<10}")

    print("\n" + "="*80)
    if all_correct:
        print("STATUS: ✅ ALL CONFIGURATIONS ARE CORRECT!")
    else:
        print("STATUS: ❌ SOME CONFIGURATIONS NEED UPDATING")
        print("\nPlease update nse_expiry_engine.py EXPIRY_DAYS with the recommended mapping above.")
    print("="*80)

    # Logout
    api.logout()
    print("\n✅ Analysis complete\n")


if __name__ == '__main__':
    find_nearest_expiries()
