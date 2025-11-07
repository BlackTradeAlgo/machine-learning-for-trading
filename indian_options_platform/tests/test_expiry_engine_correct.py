#!/usr/bin/env python3
"""
NSE Expiry Engine - Verification Test
Verifies correct expiry days and date calculations
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import date, datetime, timedelta
from core.market_data.nse_expiry_engine import NSEExpiryEngine, NSEHolidayCalendar

def get_day_name(weekday):
    """Convert weekday number to name"""
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    return days[weekday]


def main():
    """Test expiry engine with current date"""
    print("\n" + "="*80)
    print("NSE EXPIRY ENGINE - VERIFICATION TEST")
    print("="*80)

    # Initialize engine
    holiday_cal = NSEHolidayCalendar()
    engine = NSEExpiryEngine(holiday_calendar=holiday_cal)

    # Get today's date
    today = date.today()
    print(f"\n📅 TODAY'S DATE: {today.strftime('%d %B %Y, %A')}")
    print(f"   Weekday: {get_day_name(today.weekday())} (Index: {today.weekday()})")

    print("\n" + "="*80)
    print("EXPIRY DAY CONFIGURATION")
    print("="*80)

    # Show configured expiry days
    symbols = ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'SENSEX', 'BANKEX', 'MIDCPNIFTY']

    print("\n{:<15} {:<15} {:<10}".format("Symbol", "Expiry Day", "Weekday"))
    print("-" * 80)

    for symbol in symbols:
        expiry_weekday = engine.EXPIRY_DAYS[symbol]
        day_name = get_day_name(expiry_weekday)
        print(f"{symbol:<15} {day_name:<15} ({expiry_weekday})")

    # Verify critical symbols
    print("\n" + "="*80)
    print("CRITICAL VERIFICATION")
    print("="*80)

    print("\n✓ NIFTY Expiry Day:")
    nifty_day = engine.EXPIRY_DAYS['NIFTY']
    print(f"  Configured: {get_day_name(nifty_day)} (Index: {nifty_day})")
    if nifty_day == 1:  # Tuesday
        print(f"  Status: ✅ CORRECT - Tuesday")
    else:
        print(f"  Status: ❌ WRONG - Should be Tuesday (1)")

    print("\n✓ SENSEX Expiry Day:")
    sensex_day = engine.EXPIRY_DAYS['SENSEX']
    print(f"  Configured: {get_day_name(sensex_day)} (Index: {sensex_day})")
    if sensex_day == 3:  # Thursday
        print(f"  Status: ✅ CORRECT - Thursday")
    else:
        print(f"  Status: ❌ WRONG - Should be Thursday (3)")

    print("\n✓ BANKNIFTY Expiry Day:")
    bn_day = engine.EXPIRY_DAYS['BANKNIFTY']
    print(f"  Configured: {get_day_name(bn_day)} (Index: {bn_day})")
    if bn_day == 2:  # Wednesday
        print(f"  Status: ✅ CORRECT - Wednesday")
    else:
        print(f"  Status: ❌ WRONG - Should be Wednesday (2)")

    # Test next expiry calculation from TODAY
    print("\n" + "="*80)
    print("NEXT EXPIRY CALCULATION (FROM TODAY)")
    print("="*80)

    print(f"\nCalculating next expiry from: {today.strftime('%d %b %Y (%A)')}")
    print("\n{:<15} {:<20} {:<15} {:<10}".format("Symbol", "Next Expiry", "Day", "Days Away"))
    print("-" * 80)

    for symbol in symbols:
        try:
            next_expiry = engine.get_next_expiry(symbol, from_date=today, weekly=True)
            days_away = (next_expiry - today).days
            expiry_day_name = get_day_name(next_expiry.weekday())

            # Check if day matches configuration
            expected_day = engine.EXPIRY_DAYS[symbol]
            is_correct = next_expiry.weekday() == expected_day

            status = "✅" if is_correct else "❌"

            print(f"{symbol:<15} {next_expiry.strftime('%d %b %Y'):<20} {expiry_day_name:<15} {days_away:<10} {status}")

        except Exception as e:
            print(f"{symbol:<15} ERROR: {str(e)}")

    # Detailed verification for NIFTY and SENSEX
    print("\n" + "="*80)
    print("DETAILED VERIFICATION - NIFTY")
    print("="*80)

    nifty_expiry = engine.get_next_expiry('NIFTY', from_date=today)
    print(f"\nNIFTY Next Expiry: {nifty_expiry.strftime('%d %B %Y')}")
    print(f"Day: {get_day_name(nifty_expiry.weekday())}")
    print(f"Days from today: {(nifty_expiry - today).days}")
    print(f"Is Trading Day: {holiday_cal.is_trading_day(nifty_expiry)}")

    # Verify it's Tuesday
    if nifty_expiry.weekday() == 1:
        print("✅ VERIFIED: Next NIFTY expiry is on Tuesday")
    else:
        print(f"❌ ERROR: Next NIFTY expiry is on {get_day_name(nifty_expiry.weekday())}, expected Tuesday")

    print("\n" + "="*80)
    print("DETAILED VERIFICATION - SENSEX")
    print("="*80)

    sensex_expiry = engine.get_next_expiry('SENSEX', from_date=today)
    print(f"\nSENSEX Next Expiry: {sensex_expiry.strftime('%d %B %Y')}")
    print(f"Day: {get_day_name(sensex_expiry.weekday())}")
    print(f"Days from today: {(sensex_expiry - today).days}")
    print(f"Is Trading Day: {holiday_cal.is_trading_day(sensex_expiry)}")

    # Verify it's Thursday
    if sensex_expiry.weekday() == 3:
        print("✅ VERIFIED: Next SENSEX expiry is on Thursday")
    else:
        print(f"❌ ERROR: Next SENSEX expiry is on {get_day_name(sensex_expiry.weekday())}, expected Thursday")

    # Show next 4 weeks of expiries
    print("\n" + "="*80)
    print("NEXT 4 WEEKS - NIFTY EXPIRIES")
    print("="*80)

    print("\n{:<5} {:<20} {:<15}".format("Week", "Date", "Day"))
    print("-" * 80)

    current_date = today
    for week in range(1, 5):
        expiry = engine.get_next_expiry('NIFTY', from_date=current_date)
        expiry_day = get_day_name(expiry.weekday())
        print(f"{week:<5} {expiry.strftime('%d %b %Y'):<20} {expiry_day:<15}")
        current_date = expiry + timedelta(days=1)  # Move to next day after expiry

    print("\n" + "="*80)
    print("NEXT 4 WEEKS - SENSEX EXPIRIES")
    print("="*80)

    print("\n{:<5} {:<20} {:<15}".format("Week", "Date", "Day"))
    print("-" * 80)

    current_date = today
    for week in range(1, 5):
        expiry = engine.get_next_expiry('SENSEX', from_date=current_date)
        expiry_day = get_day_name(expiry.weekday())
        print(f"{week:<5} {expiry.strftime('%d %b %Y'):<20} {expiry_day:<15}")
        current_date = expiry + timedelta(days=1)

    # Test time to expiry calculation
    print("\n" + "="*80)
    print("TIME TO EXPIRY (IN YEARS - FOR OPTIONS PRICING)")
    print("="*80)

    print("\n{:<15} {:<15} {:<15}".format("Symbol", "Days", "Years"))
    print("-" * 80)

    for symbol in ['NIFTY', 'BANKNIFTY', 'SENSEX']:
        tte = engine.time_to_expiry(symbol, from_date=today)
        days = (engine.get_next_expiry(symbol, from_date=today) - today).days
        print(f"{symbol:<15} {days:<15} {tte:.6f}")

    # Monthly expiry test
    print("\n" + "="*80)
    print("MONTHLY EXPIRY (LAST OCCURRENCE OF EXPIRY DAY IN MONTH)")
    print("="*80)

    print("\n{:<15} {:<20} {:<15}".format("Symbol", "Monthly Expiry", "Day"))
    print("-" * 80)

    for symbol in ['NIFTY', 'BANKNIFTY', 'SENSEX']:
        try:
            monthly_expiry = engine.get_next_expiry(symbol, from_date=today, weekly=False)
            expiry_day = get_day_name(monthly_expiry.weekday())
            print(f"{symbol:<15} {monthly_expiry.strftime('%d %b %Y'):<20} {expiry_day:<15}")
        except Exception as e:
            print(f"{symbol:<15} ERROR: {str(e)}")

    # Final summary
    print("\n" + "="*80)
    print("FINAL VERIFICATION SUMMARY")
    print("="*80)

    all_correct = True

    print("\n✓ Configuration Check:")
    print(f"  NIFTY = Tuesday: {'✅ PASS' if engine.EXPIRY_DAYS['NIFTY'] == 1 else '❌ FAIL'}")
    print(f"  SENSEX = Thursday: {'✅ PASS' if engine.EXPIRY_DAYS['SENSEX'] == 3 else '❌ FAIL'}")
    print(f"  BANKNIFTY = Wednesday: {'✅ PASS' if engine.EXPIRY_DAYS['BANKNIFTY'] == 2 else '❌ FAIL'}")

    if engine.EXPIRY_DAYS['NIFTY'] != 1:
        all_correct = False
    if engine.EXPIRY_DAYS['SENSEX'] != 3:
        all_correct = False
    if engine.EXPIRY_DAYS['BANKNIFTY'] != 2:
        all_correct = False

    print("\n✓ Date Calculation Check:")
    nifty_next = engine.get_next_expiry('NIFTY', from_date=today)
    sensex_next = engine.get_next_expiry('SENSEX', from_date=today)

    print(f"  NIFTY next expiry is Tuesday: {'✅ PASS' if nifty_next.weekday() == 1 else '❌ FAIL'}")
    print(f"  SENSEX next expiry is Thursday: {'✅ PASS' if sensex_next.weekday() == 3 else '❌ FAIL'}")

    if nifty_next.weekday() != 1:
        all_correct = False
    if sensex_next.weekday() != 3:
        all_correct = False

    print("\n" + "="*80)
    if all_correct:
        print("STATUS: ✅ ALL TESTS PASSED - EXPIRY ENGINE IS CORRECT!")
    else:
        print("STATUS: ❌ SOME TESTS FAILED - PLEASE REVIEW")
    print("="*80 + "\n")


if __name__ == '__main__':
    main()
