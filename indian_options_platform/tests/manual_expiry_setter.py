#!/usr/bin/env python3
"""
Manual Expiry Setter
Aap actual expiry dates do, yeh automatically weekday detect kar lega
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import date, datetime

def get_day_name(weekday):
    """Convert weekday number to name"""
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    return days[weekday]


def analyze_expiries():
    """Analyze manual expiry inputs"""

    print("\n" + "="*80)
    print("MANUAL EXPIRY ANALYZER")
    print("="*80)

    # Aap yahan actual near expiry dates daal do (jo NSE/BSE pe hai)
    # Format: YYYY, MM, DD

    expiry_dates = {
        'NIFTY': [
            date(2024, 11, 14),    # Nearest expiry
            date(2024, 11, 21),    # Next expiry
            date(2024, 11, 28),    # Next expiry
        ],
        'BANKNIFTY': [
            date(2024, 11, 13),    # Nearest expiry
            date(2024, 11, 20),    # Next expiry
            date(2024, 11, 27),    # Next expiry
        ],
        'FINNIFTY': [
            date(2024, 11, 12),    # Nearest expiry
            date(2024, 11, 19),    # Next expiry
            date(2024, 11, 26),    # Next expiry
        ],
        'SENSEX': [
            date(2024, 11, 15),    # Nearest expiry
            date(2024, 11, 22),    # Next expiry
            date(2024, 11, 29),    # Next expiry
        ],
        'MIDCPNIFTY': [
            date(2024, 11, 11),    # Nearest expiry
            date(2024, 11, 18),    # Next expiry
            date(2024, 11, 25),    # Next expiry
        ],
    }

    print("\n📅 ENTERED EXPIRY DATES ANALYSIS:")
    print("="*80)

    results = {}

    for symbol, dates in expiry_dates.items():
        print(f"\n{symbol}:")
        print(f"  {'Week':<10} {'Date':<15} {'Weekday':<15}")
        print(f"  {'-'*40}")

        weekdays = []
        for i, exp_date in enumerate(dates, 1):
            weekday = exp_date.weekday()
            day_name = get_day_name(weekday)
            weekdays.append(weekday)

            print(f"  Week {i:<5} {exp_date.strftime('%d %b %Y'):<15} {day_name:<15} ({weekday})")

            if i == 1:  # Store nearest expiry
                results[symbol] = {
                    'date': exp_date,
                    'weekday': weekday,
                    'day_name': day_name
                }

        # Check consistency
        if len(set(weekdays)) == 1:
            print(f"  ✓ Consistent: All expiries on {get_day_name(weekdays[0])}")
        else:
            print(f"  ⚠️  Inconsistent weekdays: {[get_day_name(w) for w in set(weekdays)]}")

    # Generate EXPIRY_DAYS mapping
    print("\n" + "="*80)
    print("GENERATED EXPIRY_DAYS MAPPING:")
    print("="*80)

    print("\nCopy this to nse_expiry_engine.py:")
    print("\nEXPIRY_DAYS = {")
    for symbol, info in results.items():
        print(f"    '{symbol}': {info['weekday']},  # {info['day_name']}")
    print("}")

    # Show summary table
    print("\n" + "="*80)
    print("SUMMARY:")
    print("="*80)

    print(f"\n{'Symbol':<15} {'Expiry Day':<15} {'Weekday Index':<15}")
    print("-" * 80)

    for symbol, info in results.items():
        print(f"{symbol:<15} {info['day_name']:<15} {info['weekday']:<15}")

    print("\n" + "="*80)
    print("INSTRUCTIONS:")
    print("="*80)
    print("""
1. Verify the dates above match NSE/BSE actual expiry schedule
2. If correct, copy the EXPIRY_DAYS mapping to nse_expiry_engine.py
3. If dates are wrong, update the expiry_dates dictionary in this file
4. Re-run this script to regenerate the mapping
""")

    print("\n✅ Analysis complete\n")


if __name__ == '__main__':
    analyze_expiries()
