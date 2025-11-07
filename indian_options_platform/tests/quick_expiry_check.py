#!/usr/bin/env python3
"""Quick check of expiry data"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from dotenv import load_dotenv
load_dotenv()

from core.market_data.angel_one_api import AngelOneAPI

api_key = os.getenv('ANGEL_API_KEY')
client_id = os.getenv('ANGEL_CLIENT_ID')
password = os.getenv('ANGEL_PASSWORD')
totp_secret = os.getenv('ANGEL_TOTP_SECRET')

print("Connecting...")
api = AngelOneAPI(api_key, client_id, password, totp_secret)
api.login()

# Get NIFTY options
nifty = api.instrument_master[
    (api.instrument_master['name'] == 'NIFTY') &
    (api.instrument_master['instrumenttype'].isin(['OPTIDX', 'OPTSTK']))
].head(20)

print("\nSample NIFTY options:")
print(nifty[['symbol', 'expiry', 'strike']].to_string())

print("\nUnique expiries (first 10):")
print(api.instrument_master[api.instrument_master['name'] == 'NIFTY']['expiry'].unique()[:10])

api.logout()
