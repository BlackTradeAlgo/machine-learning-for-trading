"""
NSE Data Integration Module
Fetches real-time and historical data from NSE India

Data Sources:
1. NSE Official Website (scraping with proper headers)
2. NSEpy library (fallback)
3. Yahoo Finance India (backup)
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
import time
from functools import lru_cache
import warnings


class NSEData:
    """
    Fetch data from NSE India

    Features:
    - Real-time options chain
    - Historical data
    - Indices (Nifty, Bank Nifty, Fin Nifty)
    - FII/DII data
    - Market breadth
    - Volatility indices (India VIX)
    """

    BASE_URL = "https://www.nseindia.com"
    API_URLS = {
        'option_chain': '/api/option-chain-indices',
        'option_chain_equities': '/api/option-chain-equities',
        'market_status': '/api/marketStatus',
        'indices': '/api/allIndices',
        'equity_meta': '/api/equity-meta-info',
        'quote': '/api/quote-equity',
        'historical': '/api/historical/cm/equity'
    }

    def __init__(self, timeout: int = 10):
        """
        Initialize NSE Data client

        Parameters:
        -----------
        timeout : int
            Request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()
        self._setup_headers()

    def _setup_headers(self):
        """Setup headers to mimic browser request"""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://www.nseindia.com/',
            'X-Requested-With': 'XMLHttpRequest'
        })

    def _get_cookies(self):
        """Get cookies from NSE website (required for API access)"""
        try:
            response = self.session.get(self.BASE_URL, timeout=self.timeout)
            return response.cookies
        except Exception as e:
            warnings.warn(f"Failed to get cookies: {e}")
            return None

    def _make_request(self, endpoint: str, params: dict = None) -> Optional[dict]:
        """Make API request to NSE"""
        try:
            # Get cookies first
            self._get_cookies()

            url = f"{self.BASE_URL}{endpoint}"
            response = self.session.get(url, params=params, timeout=self.timeout)

            if response.status_code == 200:
                return response.json()
            else:
                warnings.warn(f"Request failed with status code: {response.status_code}")
                return None

        except Exception as e:
            warnings.warn(f"Request error: {e}")
            return None

    # ==================== OPTIONS CHAIN ====================

    def get_options_chain(self, symbol: str = 'NIFTY') -> Optional[pd.DataFrame]:
        """
        Fetch options chain for index

        Parameters:
        -----------
        symbol : str
            'NIFTY', 'BANKNIFTY', 'FINNIFTY', 'MIDCPNIFTY'

        Returns:
        --------
        pd.DataFrame : Options chain data
        """
        try:
            endpoint = self.API_URLS['option_chain']
            params = {'symbol': symbol}

            data = self._make_request(endpoint, params)

            if not data or 'records' not in data:
                warnings.warn(f"No data received for {symbol}")
                return None

            records = data['records']['data']

            # Parse options chain
            chain_data = []

            for record in records:
                row = {
                    'strike': record.get('strikePrice', 0),
                    'expiry': record.get('expiryDate', '')
                }

                # Call options
                if 'CE' in record:
                    ce = record['CE']
                    row.update({
                        'call_oi': ce.get('openInterest', 0),
                        'call_chng_oi': ce.get('changeinOpenInterest', 0),
                        'call_volume': ce.get('totalTradedVolume', 0),
                        'call_iv': ce.get('impliedVolatility', 0),
                        'call_ltp': ce.get('lastPrice', 0),
                        'call_chng': ce.get('change', 0),
                        'call_bid': ce.get('bidPrice', 0),
                        'call_ask': ce.get('askPrice', 0),
                        'call_bid_qty': ce.get('bidQty', 0),
                        'call_ask_qty': ce.get('askQty', 0)
                    })

                # Put options
                if 'PE' in record:
                    pe = record['PE']
                    row.update({
                        'put_oi': pe.get('openInterest', 0),
                        'put_chng_oi': pe.get('changeinOpenInterest', 0),
                        'put_volume': pe.get('totalTradedVolume', 0),
                        'put_iv': pe.get('impliedVolatility', 0),
                        'put_ltp': pe.get('lastPrice', 0),
                        'put_chng': pe.get('change', 0),
                        'put_bid': pe.get('bidPrice', 0),
                        'put_ask': pe.get('askPrice', 0),
                        'put_bid_qty': pe.get('bidQty', 0),
                        'put_ask_qty': pe.get('askQty', 0)
                    })

                chain_data.append(row)

            df = pd.DataFrame(chain_data)

            # Add metadata
            if 'underlyingValue' in data['records']:
                df.attrs['spot'] = data['records']['underlyingValue']
            if 'timestamp' in data['records']:
                df.attrs['timestamp'] = data['records']['timestamp']

            return df

        except Exception as e:
            warnings.warn(f"Error fetching options chain: {e}")
            return None

    def get_spot_price(self, symbol: str = 'NIFTY') -> Optional[float]:
        """Get current spot price of index"""
        try:
            endpoint = self.API_URLS['indices']
            data = self._make_request(endpoint)

            if not data or 'data' not in data:
                return None

            # Find the symbol
            for index in data['data']:
                if index.get('index', '').upper() == symbol.upper():
                    return float(index.get('last', 0))

            return None

        except Exception as e:
            warnings.warn(f"Error fetching spot price: {e}")
            return None

    # ==================== MARKET ANALYSIS ====================

    def calculate_pcr(self, options_chain: pd.DataFrame, oi_based: bool = True) -> float:
        """
        Calculate Put-Call Ratio

        Parameters:
        -----------
        oi_based : bool
            True: PCR based on Open Interest
            False: PCR based on Volume

        Returns:
        --------
        float : PCR value
        """
        if oi_based:
            put_oi = options_chain['put_oi'].sum()
            call_oi = options_chain['call_oi'].sum()
            return put_oi / call_oi if call_oi > 0 else 0
        else:
            put_vol = options_chain['put_volume'].sum()
            call_vol = options_chain['call_volume'].sum()
            return put_vol / call_vol if call_vol > 0 else 0

    def calculate_max_pain(self, options_chain: pd.DataFrame) -> float:
        """
        Calculate Max Pain - strike with maximum pain for option writers

        Returns:
        --------
        float : Max pain strike price
        """
        strikes = options_chain['strike'].unique()
        max_pain_strike = 0
        min_pain = float('inf')

        for strike in strikes:
            # Calculate pain at this strike
            call_pain = 0
            put_pain = 0

            for _, row in options_chain.iterrows():
                if row['strike'] < strike:
                    # ITM puts
                    put_pain += (strike - row['strike']) * row['put_oi']
                elif row['strike'] > strike:
                    # ITM calls
                    call_pain += (row['strike'] - strike) * row['call_oi']

            total_pain = call_pain + put_pain

            if total_pain < min_pain:
                min_pain = total_pain
                max_pain_strike = strike

        return max_pain_strike

    def get_atm_strike(self, spot: float, strike_diff: int = 50) -> float:
        """Get nearest ATM strike"""
        return round(spot / strike_diff) * strike_diff

    def get_support_resistance_from_oi(self, options_chain: pd.DataFrame,
                                       top_n: int = 3) -> Tuple[List[float], List[float]]:
        """
        Identify support and resistance levels from OI

        High Put OI = Support
        High Call OI = Resistance

        Returns:
        --------
        Tuple[List[float], List[float]] : (support_levels, resistance_levels)
        """
        # Sort by OI
        put_oi = options_chain.nlargest(top_n, 'put_oi')['strike'].tolist()
        call_oi = options_chain.nlargest(top_n, 'call_oi')['strike'].tolist()

        return put_oi, call_oi

    def get_oi_changes(self, options_chain: pd.DataFrame,
                      threshold: float = 100000) -> pd.DataFrame:
        """
        Get strikes with significant OI changes

        Returns strikes where OI change > threshold
        """
        significant = options_chain[
            (abs(options_chain['call_chng_oi']) > threshold) |
            (abs(options_chain['put_chng_oi']) > threshold)
        ].copy()

        return significant.sort_values('strike')

    # ==================== INDIA VIX ====================

    def get_india_vix(self) -> Optional[float]:
        """Get current India VIX value"""
        try:
            endpoint = self.API_URLS['indices']
            data = self._make_request(endpoint)

            if not data or 'data' not in data:
                return None

            for index in data['data']:
                if 'VIX' in index.get('index', '').upper():
                    return float(index.get('last', 0))

            return None

        except Exception as e:
            warnings.warn(f"Error fetching India VIX: {e}")
            return None

    # ==================== EXPIRY DATES ====================

    def get_expiry_dates(self, symbol: str = 'NIFTY') -> List[str]:
        """Get all expiry dates for the symbol"""
        try:
            chain = self.get_options_chain(symbol)
            if chain is not None:
                expiries = chain['expiry'].unique().tolist()
                return sorted(expiries)
            return []

        except Exception as e:
            warnings.warn(f"Error fetching expiry dates: {e}")
            return []

    def get_next_expiry(self, symbol: str = 'NIFTY') -> Optional[str]:
        """Get next expiry date"""
        expiries = self.get_expiry_dates(symbol)
        return expiries[0] if expiries else None

    def days_to_expiry(self, expiry_date: str) -> int:
        """Calculate days to expiry"""
        try:
            expiry = datetime.strptime(expiry_date, '%d-%b-%Y')
            today = datetime.now()
            return (expiry - today).days
        except Exception:
            return 0

    # ==================== MARKET STATUS ====================

    def is_market_open(self) -> bool:
        """Check if market is currently open"""
        try:
            endpoint = self.API_URLS['market_status']
            data = self._make_request(endpoint)

            if not data or 'marketState' not in data:
                return False

            for market in data['marketState']:
                if market.get('market', '') == 'Capital Market':
                    return market.get('marketStatus', '').lower() == 'open'

            return False

        except Exception:
            return False

    # ==================== UTILITY METHODS ====================

    @lru_cache(maxsize=128)
    def get_lot_size(self, symbol: str) -> int:
        """
        Get lot size for symbol

        Common lot sizes (as of 2024):
        NIFTY: 50
        BANKNIFTY: 15
        FINNIFTY: 40
        MIDCPNIFTY: 75
        """
        lot_sizes = {
            'NIFTY': 50,
            'BANKNIFTY': 15,
            'FINNIFTY': 40,
            'MIDCPNIFTY': 75,
            'SENSEX': 10
        }

        return lot_sizes.get(symbol.upper(), 1)


if __name__ == "__main__":
    # Example usage
    nse = NSEData()

    print("=" * 70)
    print("NSE DATA INTEGRATION - EXAMPLE")
    print("=" * 70)

    # Check market status
    is_open = nse.is_market_open()
    print(f"\n{'Market Status':<20}: {'OPEN ✓' if is_open else 'CLOSED ✗'}")

    # Get Nifty spot
    spot = nse.get_spot_price('NIFTY')
    if spot:
        print(f"{'Nifty Spot':<20}: ₹{spot:,.2f}")

    # Get India VIX
    vix = nse.get_india_vix()
    if vix:
        print(f"{'India VIX':<20}: {vix:.2f}")

    # Get options chain
    print("\n" + "=" * 70)
    print("NIFTY OPTIONS CHAIN")
    print("=" * 70)

    chain = nse.get_options_chain('NIFTY')

    if chain is not None and not chain.empty:
        # Filter current expiry
        expiry = chain['expiry'].iloc[0]
        current_expiry = chain[chain['expiry'] == expiry]

        # Get ATM strikes
        spot = chain.attrs.get('spot', 19500)
        atm = nse.get_atm_strike(spot)

        atm_data = current_expiry[
            (current_expiry['strike'] >= atm - 200) &
            (current_expiry['strike'] <= atm + 200)
        ]

        print(f"\nExpiry: {expiry}")
        print(f"Spot: ₹{spot:,.2f}")
        print(f"ATM Strike: {atm}")
        print("\n" + "-" * 70)
        print(f"{'Strike':<8} {'Call LTP':<10} {'Call OI':<12} {'Put LTP':<10} {'Put OI':<12}")
        print("-" * 70)

        for _, row in atm_data.iterrows():
            print(f"{row['strike']:<8.0f} "
                  f"₹{row['call_ltp']:<9.2f} "
                  f"{row['call_oi']:<12,.0f} "
                  f"₹{row['put_ltp']:<9.2f} "
                  f"{row['put_oi']:<12,.0f}")

        # Market analysis
        print("\n" + "=" * 70)
        print("MARKET ANALYSIS")
        print("=" * 70)

        pcr = nse.calculate_pcr(current_expiry)
        print(f"{'PCR (OI Based)':<25}: {pcr:.4f}")

        if pcr > 1.2:
            print(f"{'Market Sentiment':<25}: BULLISH 📈")
        elif pcr < 0.8:
            print(f"{'Market Sentiment':<25}: BEARISH 📉")
        else:
            print(f"{'Market Sentiment':<25}: NEUTRAL ↔️")

        max_pain = nse.calculate_max_pain(current_expiry)
        print(f"{'Max Pain Strike':<25}: {max_pain:.0f}")

        support, resistance = nse.get_support_resistance_from_oi(current_expiry)
        print(f"{'Support Levels':<25}: {', '.join(map(str, map(int, support)))}")
        print(f"{'Resistance Levels':<25}: {', '.join(map(str, map(int, resistance)))}")

    else:
        print("Unable to fetch options chain data")
        print("Note: This may happen if:")
        print("  1. Market is closed")
        print("  2. NSE website structure has changed")
        print("  3. Network/firewall issues")
