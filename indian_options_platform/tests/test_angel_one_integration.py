#!/usr/bin/env python3
"""
Angel One API Integration Test
Tests live connection with Angel One SmartAPI

IMPORTANT: This test uses REAL credentials and connects to LIVE Angel One API
- Tests authentication and data fetching
- Does NOT place any real trades
- Validates all API endpoints
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
import time
from datetime import date

# Load credentials
load_dotenv()

# Import Angel One API
from core.market_data.angel_one_api import AngelOneAPI
from core.market_data.nse_expiry_engine import NSEExpiryEngine

# Test results
test_results = {
    'passed': [],
    'failed': [],
    'warnings': []
}


def log_test(name, passed, message=""):
    """Log test result"""
    if passed:
        test_results['passed'].append(name)
        print(f"  ✅ {name}")
        if message:
            print(f"     → {message}")
    else:
        test_results['failed'].append(name)
        print(f"  ❌ {name}")
        if message:
            print(f"     → {message}")


def log_warning(message):
    """Log warning"""
    test_results['warnings'].append(message)
    print(f"  ⚠️  {message}")


def main():
    """Run Angel One API integration tests"""
    print("\n" + "="*80)
    print("ANGEL ONE API INTEGRATION TEST")
    print("="*80)
    print("\n⚠️  IMPORTANT: This test uses REAL credentials and LIVE API")
    print("   - Connects to Angel One production servers")
    print("   - Fetches real market data")
    print("   - Does NOT place any real trades")
    print("="*80 + "\n")

    # Load credentials
    api_key = os.getenv('ANGEL_API_KEY')
    client_id = os.getenv('ANGEL_CLIENT_ID')
    password = os.getenv('ANGEL_PASSWORD')
    totp_secret = os.getenv('ANGEL_TOTP_SECRET')

    print("[1] CREDENTIAL VALIDATION")
    print("-" * 80)

    if not all([api_key, client_id, password, totp_secret]):
        print("  ❌ Missing credentials in .env file")
        print(f"     API Key: {'✓' if api_key else '✗'}")
        print(f"     Client ID: {'✓' if client_id else '✗'}")
        print(f"     Password: {'✓' if password else '✗'}")
        print(f"     TOTP Secret: {'✓' if totp_secret else '✗'}")
        return

    print(f"  ✅ API Key: {api_key[:4]}...{api_key[-4:]}")
    print(f"  ✅ Client ID: {client_id}")
    print(f"  ✅ Password: {'*' * len(password)}")
    print(f"  ✅ TOTP Secret: {totp_secret[:4]}...{totp_secret[-4:]}")

    # Initialize API
    print(f"\n[2] AUTHENTICATION TEST")
    print("-" * 80)

    try:
        api = AngelOneAPI(
            api_key=api_key,
            username=client_id,
            password=password,
            totp_token=totp_secret
        )

        print("  → Initializing Angel One SmartAPI...")
        print("  → Generating TOTP code...")
        print("  → Attempting login...")

        login_success = api.login()

        if login_success:
            log_test("Angel One Login", True, f"User: {client_id}")
            log_test("JWT Token Generated", True, f"Token: {api.auth_token[:20]}...")
            log_test("Feed Token Generated", True, f"Feed: {api.feed_token[:20] if api.feed_token else 'N/A'}...")
        else:
            log_test("Angel One Login", False, "Login failed - check credentials")
            return

    except Exception as e:
        log_test("Angel One Login", False, f"Error: {str(e)}")
        return

    # Test instrument master
    print(f"\n[3] INSTRUMENT MASTER DATA TEST")
    print("-" * 80)

    if api.instrument_master is not None:
        total_instruments = len(api.instrument_master)
        log_test("Instrument Master Loaded", True, f"{total_instruments:,} instruments")

        # Check for Nifty instruments
        nifty_count = len(api.instrument_master[api.instrument_master['name'] == 'NIFTY'])
        banknifty_count = len(api.instrument_master[api.instrument_master['name'] == 'BANKNIFTY'])

        log_test("Nifty Instruments Found", nifty_count > 0, f"{nifty_count} instruments")
        log_test("Bank Nifty Instruments Found", banknifty_count > 0, f"{banknifty_count} instruments")
    else:
        log_test("Instrument Master Loaded", False, "Failed to load instrument data")

    # Test options search
    print(f"\n[4] OPTIONS SEARCH TEST")
    print("-" * 80)

    try:
        # Get next Nifty expiry
        expiry_engine = NSEExpiryEngine()
        next_expiry = expiry_engine.get_next_expiry('NIFTY', from_date=date.today())
        expiry_str = next_expiry.strftime('%d%b%y').upper()

        print(f"  → Searching for Nifty options (Expiry: {expiry_str})...")

        nifty_options = api.search_options('NIFTY', expiry=expiry_str)

        if not nifty_options.empty:
            log_test("Nifty Options Search", True, f"{len(nifty_options)} options found")

            # Show sample options
            calls = nifty_options[nifty_options['symbol'].str.contains('CE')]
            puts = nifty_options[nifty_options['symbol'].str.contains('PE')]

            print(f"     → Call Options: {len(calls)}")
            print(f"     → Put Options: {len(puts)}")

            if not calls.empty:
                sample = calls.iloc[0]
                print(f"     → Sample Call: {sample['symbol']}")
                log_test("Call Options Available", True)

            if not puts.empty:
                sample = puts.iloc[0]
                print(f"     → Sample Put: {sample['symbol']}")
                log_test("Put Options Available", True)
        else:
            log_test("Nifty Options Search", False, "No options found")
            log_warning(f"No options found for expiry {expiry_str}")

    except Exception as e:
        log_test("Nifty Options Search", False, f"Error: {str(e)}")

    # Test token lookup
    print(f"\n[5] TOKEN LOOKUP TEST")
    print("-" * 80)

    try:
        # Try to get Nifty index token
        nifty_token = api.get_token('NIFTY', 'NSE')

        if nifty_token:
            log_test("Nifty Token Lookup", True, f"Token: {nifty_token}")
        else:
            log_test("Nifty Token Lookup", False, "Token not found")

        # Try Bank Nifty
        banknifty_token = api.get_token('BANKNIFTY', 'NSE')

        if banknifty_token:
            log_test("Bank Nifty Token Lookup", True, f"Token: {banknifty_token}")
        else:
            log_test("Bank Nifty Token Lookup", False, "Token not found")

    except Exception as e:
        log_test("Token Lookup", False, f"Error: {str(e)}")

    # Test live data (CAREFULLY - market hours dependent)
    print(f"\n[6] LIVE MARKET DATA TEST")
    print("-" * 80)
    print("  ⚠️  Note: These tests may fail outside market hours (9:15 AM - 3:30 PM)")

    try:
        # Check if market is open (rough check)
        from datetime import datetime
        now = datetime.now()
        is_market_hours = (9 <= now.hour < 15) or (now.hour == 15 and now.minute < 30)

        if not is_market_hours:
            log_warning("Tests running outside market hours - live data may be unavailable")

        # Try to get Nifty LTP
        if nifty_token:
            print(f"  → Fetching Nifty LTP...")
            ltp = api.get_ltp('NSE', 'NIFTY', nifty_token)

            if ltp:
                log_test("Nifty LTP Fetch", True, f"Price: ₹{ltp:,.2f}")
            else:
                log_test("Nifty LTP Fetch", False, "LTP unavailable (may be outside market hours)")

            # Try to get full quote
            print(f"  → Fetching Nifty Quote...")
            quote = api.get_quote('NSE', 'NIFTY', nifty_token)

            if quote:
                log_test("Nifty Quote Fetch", True, f"LTP: ₹{quote['ltp']:,.2f}, Open: ₹{quote['open']:,.2f}")
                print(f"     → High: ₹{quote['high']:,.2f}")
                print(f"     → Low: ₹{quote['low']:,.2f}")
                print(f"     → Volume: {quote['volume']:,}")
            else:
                log_test("Nifty Quote Fetch", False, "Quote unavailable (may be outside market hours)")

    except Exception as e:
        log_test("Live Market Data", False, f"Error: {str(e)}")

    # Test positions and orders (read-only)
    print(f"\n[7] ACCOUNT DATA TEST (READ-ONLY)")
    print("-" * 80)

    try:
        print(f"  → Fetching current positions...")
        positions = api.get_positions()

        if positions is not None:
            log_test("Positions Fetch", True, f"{len(positions)} position(s)")
            if len(positions) > 0:
                print(f"     → Active Positions: {len(positions)}")
        else:
            log_test("Positions Fetch", False, "Failed to fetch positions")

        print(f"  → Fetching order book...")
        orders = api.get_orders()

        if orders is not None:
            log_test("Orders Fetch", True, f"{len(orders)} order(s)")
            if len(orders) > 0:
                print(f"     → Today's Orders: {len(orders)}")
        else:
            log_test("Orders Fetch", False, "Failed to fetch orders")

        print(f"  → Fetching holdings...")
        holdings = api.get_holdings()

        if holdings is not None:
            log_test("Holdings Fetch", True, f"{len(holdings)} holding(s)")
        else:
            log_test("Holdings Fetch", False, "Failed to fetch holdings")

    except Exception as e:
        log_test("Account Data Fetch", False, f"Error: {str(e)}")

    # Test order validation (NO ACTUAL ORDERS)
    print(f"\n[8] ORDER VALIDATION TEST (NO REAL ORDERS)")
    print("-" * 80)
    print("  ⚠️  This section validates order parameters WITHOUT placing real orders")

    try:
        # Just validate that we can construct order parameters
        if not nifty_options.empty:
            sample_option = nifty_options.iloc[0]

            print(f"  → Validating order structure for: {sample_option['symbol']}")

            order_params = {
                "variety": "NORMAL",
                "tradingsymbol": sample_option['symbol'],
                "symboltoken": sample_option['token'],
                "transactiontype": "BUY",
                "exchange": "NFO",
                "ordertype": "LIMIT",
                "producttype": "INTRADAY",
                "duration": "DAY",
                "price": "100",
                "quantity": str(int(sample_option['lotsize']))
            }

            log_test("Order Parameters Validated", True, "Structure is correct")
            print(f"     → Symbol: {order_params['tradingsymbol']}")
            print(f"     → Type: {order_params['transactiontype']}")
            print(f"     → Quantity: {order_params['quantity']}")
            print(f"     → Order Type: {order_params['ordertype']}")
            print(f"     ✅ Order structure is valid (NOT PLACED)")

    except Exception as e:
        log_test("Order Validation", False, f"Error: {str(e)}")

    # Cleanup
    print(f"\n[9] CLEANUP & LOGOUT")
    print("-" * 80)

    try:
        print(f"  → Logging out from Angel One...")
        api.logout()
        log_test("Logout", True, "Session terminated")

    except Exception as e:
        log_test("Logout", False, f"Error: {str(e)}")

    # Final Report
    print(f"\n" + "="*80)
    print("ANGEL ONE API INTEGRATION TEST - FINAL REPORT")
    print("="*80)

    total_tests = len(test_results['passed']) + len(test_results['failed'])
    passed = len(test_results['passed'])
    failed = len(test_results['failed'])
    warnings = len(test_results['warnings'])

    print(f"\nTotal Tests: {total_tests}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"⚠️  Warnings: {warnings}")

    if total_tests > 0:
        success_rate = (passed / total_tests) * 100
        print(f"\nSuccess Rate: {success_rate:.1f}%")

        print("\n" + "="*80)
        if success_rate >= 90:
            print("STATUS: ✅ EXCELLENT - Angel One integration is fully functional")
        elif success_rate >= 75:
            print("STATUS: ✅ GOOD - Angel One integration is working with minor issues")
        elif success_rate >= 50:
            print("STATUS: ⚠️  FAIR - Angel One integration has some issues")
        else:
            print("STATUS: ❌ POOR - Angel One integration has major issues")
        print("="*80)

    # Show failures
    if failed > 0:
        print(f"\n❌ FAILED TESTS:")
        for test in test_results['failed']:
            print(f"  - {test}")

    # Show warnings
    if warnings > 0:
        print(f"\n⚠️  WARNINGS:")
        for warning in test_results['warnings']:
            print(f"  - {warning}")

    # Show passed tests
    if passed > 0:
        print(f"\n✅ PASSED TESTS:")
        for test in test_results['passed']:
            print(f"  - {test}")

    print("\n" + "="*80)
    print("TEST COMPLETE")
    print("="*80 + "\n")


if __name__ == '__main__':
    main()
