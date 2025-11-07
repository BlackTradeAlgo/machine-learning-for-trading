"""
NSE Options Expiry Engine
Calculates expiry dates for NSE/BSE options

Expiry Rules (✅ VERIFIED FROM ANGEL ONE - Nov 2025):
------------------------------------------------------
1. Nifty Weekly: Every Tuesday (Verified: 11 Nov 2025)
2. Nifty Monthly: Last Tuesday of month
3. Bank Nifty Weekly: Every Tuesday (Verified: 25 Nov 2025)
4. Bank Nifty Monthly: Last Tuesday of month
5. Fin Nifty Weekly: Every Tuesday (Verified: 25 Nov 2025)
6. Sensex Weekly: Every Thursday (Verified: 13 Nov 2025 - BSE)
7. Sensex Monthly: Last Thursday of month
8. Midcap Nifty Weekly: Every Tuesday (Verified: 25 Nov 2025)

All expiries are on market open day (if holiday, previous trading day)
"""

from datetime import datetime, timedelta, date
from typing import List, Optional, Tuple, Dict
import calendar
import os
import pandas as pd


class NSEExpiryEngine:
    """NSE/BSE Options Expiry Engine"""

    # Expiry weekdays (0=Monday, 1=Tuesday, ..., 6=Sunday)
    # ✅ VERIFIED FROM ANGEL ONE DATA (Nov 2025)
    EXPIRY_DAYS = {
        'NIFTY': 1,        # Tuesday (Verified: 11 Nov 2025)
        'BANKNIFTY': 1,    # Tuesday (Verified: 25 Nov 2025)
        'FINNIFTY': 1,     # Tuesday (Verified: 25 Nov 2025)
        'SENSEX': 3,       # Thursday (Verified: 13 Nov 2025)
        'BANKEX': 3,       # Thursday (BSE - assumed same as SENSEX)
        'MIDCPNIFTY': 1    # Tuesday (Verified: 25 Nov 2025)
    }

    def __init__(self, holiday_calendar: Optional['NSEHolidayCalendar'] = None):
        """
        Initialize Expiry Engine

        Parameters:
        -----------
        holiday_calendar : NSEHolidayCalendar
            Holiday calendar instance (optional)
        """
        self.holiday_calendar = holiday_calendar

    def get_next_expiry(self, symbol: str = 'NIFTY',
                       from_date: Optional[date] = None,
                       weekly: bool = True) -> date:
        """
        Get next expiry date for given symbol

        Parameters:
        -----------
        symbol : str
            'NIFTY', 'BANKNIFTY', 'FINNIFTY', 'SENSEX', etc.
        from_date : date
            Start date (default: today)
        weekly : bool
            True for weekly expiry, False for monthly

        Returns:
        --------
        date : Next expiry date

        Examples:
        ---------
        >>> engine = NSEExpiryEngine()
        >>> engine.get_next_expiry('NIFTY')
        datetime.date(2025, 11, 13)  # Next Thursday

        >>> engine.get_next_expiry('NIFTY', weekly=False)
        datetime.date(2025, 11, 27)  # Last Thursday of month
        """
        if from_date is None:
            from_date = date.today()

        symbol = symbol.upper()

        if symbol not in self.EXPIRY_DAYS:
            raise ValueError(f"Unknown symbol: {symbol}. Supported: {list(self.EXPIRY_DAYS.keys())}")

        expiry_weekday = self.EXPIRY_DAYS[symbol]

        if weekly:
            # Next weekly expiry
            expiry = self._get_next_weekday(from_date, expiry_weekday)
        else:
            # Monthly expiry (last occurrence of weekday in month)
            expiry = self._get_monthly_expiry(from_date, expiry_weekday)

        # Adjust for holidays
        if self.holiday_calendar:
            expiry = self._adjust_for_holiday(expiry)

        return expiry

    def get_all_expiries(self, symbol: str = 'NIFTY',
                        start_date: Optional[date] = None,
                        end_date: Optional[date] = None,
                        weekly: bool = True,
                        count: int = 10) -> List[date]:
        """
        Get multiple expiry dates

        Parameters:
        -----------
        symbol : str
            Symbol name
        start_date : date
            Start date (default: today)
        end_date : date
            End date (default: None)
        weekly : bool
            Weekly or monthly expiries
        count : int
            Number of expiries to return (if end_date not provided)

        Returns:
        --------
        List[date] : List of expiry dates

        Examples:
        ---------
        >>> engine.get_all_expiries('NIFTY', count=4)
        [datetime.date(2025, 11, 13),
         datetime.date(2025, 11, 20),
         datetime.date(2025, 11, 27),
         datetime.date(2025, 12, 4)]
        """
        if start_date is None:
            start_date = date.today()

        expiries = []
        current_date = start_date

        while True:
            expiry = self.get_next_expiry(symbol, current_date, weekly)

            if end_date and expiry > end_date:
                break

            if not end_date and len(expiries) >= count:
                break

            expiries.append(expiry)
            current_date = expiry + timedelta(days=1)

        return expiries

    def is_expiry_day(self, check_date: date, symbol: str = 'NIFTY',
                     weekly: bool = True) -> bool:
        """
        Check if given date is an expiry day

        Parameters:
        -----------
        check_date : date
            Date to check
        symbol : str
            Symbol name
        weekly : bool
            Check weekly or monthly expiry

        Returns:
        --------
        bool : True if expiry day
        """
        expiry = self.get_next_expiry(symbol, check_date, weekly)
        return expiry == check_date

    def days_to_expiry(self, symbol: str = 'NIFTY',
                      from_date: Optional[date] = None,
                      weekly: bool = True) -> int:
        """
        Get days to next expiry

        Parameters:
        -----------
        symbol : str
            Symbol name
        from_date : date
            From date (default: today)
        weekly : bool
            Weekly or monthly expiry

        Returns:
        --------
        int : Days to expiry
        """
        if from_date is None:
            from_date = date.today()

        expiry = self.get_next_expiry(symbol, from_date, weekly)
        return (expiry - from_date).days

    def time_to_expiry(self, symbol: str = 'NIFTY',
                      from_date: Optional[date] = None,
                      weekly: bool = True) -> float:
        """
        Get time to expiry in years (for options pricing)

        Parameters:
        -----------
        symbol : str
            Symbol name
        from_date : date
            From date (default: today)
        weekly : bool
            Weekly or monthly expiry

        Returns:
        --------
        float : Time to expiry in years

        Examples:
        ---------
        >>> engine.time_to_expiry('NIFTY')
        0.0164  # ~6 days to expiry
        """
        days = self.days_to_expiry(symbol, from_date, weekly)
        return days / 365.0

    def get_expiry_series(self, symbol: str = 'NIFTY',
                         weekly: bool = True) -> Tuple[date, date, date]:
        """
        Get current, next, and far expiry dates

        Parameters:
        -----------
        symbol : str
            Symbol name
        weekly : bool
            Weekly or monthly

        Returns:
        --------
        Tuple[date, date, date] : (current, next, far) expiry dates

        Examples:
        ---------
        >>> engine.get_expiry_series('NIFTY')
        (datetime.date(2025, 11, 13),
         datetime.date(2025, 11, 20),
         datetime.date(2025, 11, 27))
        """
        expiries = self.get_all_expiries(symbol, weekly=weekly, count=3)

        if len(expiries) < 3:
            expiries.extend([None] * (3 - len(expiries)))

        return tuple(expiries[:3])

    def get_monthly_expiry_from_weekly(self, symbol: str = 'NIFTY',
                                       from_date: Optional[date] = None) -> date:
        """
        Get monthly expiry date for symbols with weekly expiries

        Parameters:
        -----------
        symbol : str
            Symbol name
        from_date : date
            From date

        Returns:
        --------
        date : Monthly expiry date
        """
        return self.get_next_expiry(symbol, from_date, weekly=False)

    # ==================== PRIVATE METHODS ====================

    def _get_next_weekday(self, from_date: date, target_weekday: int) -> date:
        """Get next occurrence of target weekday"""
        days_ahead = target_weekday - from_date.weekday()

        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7

        return from_date + timedelta(days=days_ahead)

    def _get_monthly_expiry(self, from_date: date, expiry_weekday: int) -> date:
        """Get last occurrence of weekday in month"""
        # Get last day of current month
        year = from_date.year
        month = from_date.month

        # Check if we need next month (if current month's expiry passed)
        last_day = calendar.monthrange(year, month)[1]
        last_date = date(year, month, last_day)

        # Find last occurrence of expiry weekday
        last_expiry = self._get_last_weekday_of_month(year, month, expiry_weekday)

        # If this month's expiry has passed, get next month's
        if last_expiry < from_date:
            if month == 12:
                year += 1
                month = 1
            else:
                month += 1

            last_expiry = self._get_last_weekday_of_month(year, month, expiry_weekday)

        return last_expiry

    def _get_last_weekday_of_month(self, year: int, month: int,
                                   weekday: int) -> date:
        """Get last occurrence of weekday in given month"""
        # Get last day of month
        last_day = calendar.monthrange(year, month)[1]
        last_date = date(year, month, last_day)

        # Work backwards to find last occurrence of weekday
        while last_date.weekday() != weekday:
            last_date -= timedelta(days=1)

        return last_date

    def _adjust_for_holiday(self, expiry_date: date) -> date:
        """Adjust expiry for holidays (use previous trading day)"""
        adjusted = expiry_date

        while self.holiday_calendar.is_holiday(adjusted):
            adjusted -= timedelta(days=1)

        return adjusted

    def __repr__(self) -> str:
        return f"<NSEExpiryEngine: {len(self.EXPIRY_DAYS)} symbols>"

    # ==================== METHOD 2: DYNAMIC EXPIRY FETCHING ====================

    @classmethod
    def fetch_expiries_from_angel_one(cls, api_key: str = None, client_id: str = None,
                                      password: str = None, totp_secret: str = None) -> Dict[str, Dict]:
        """
        METHOD 2: Fetch actual expiries from Angel One API and auto-detect weekdays

        This method connects to Angel One, fetches real expiry data for all symbols,
        and automatically calculates the expiry weekday for each symbol.

        Parameters:
        -----------
        api_key : str
            Angel One API key (optional, reads from env if not provided)
        client_id : str
            Angel One client ID (optional, reads from env if not provided)
        password : str
            Angel One password (optional, reads from env if not provided)
        totp_secret : str
            Angel One TOTP secret (optional, reads from env if not provided)

        Returns:
        --------
        Dict[str, Dict] : Dictionary with symbol data
            {
                'NIFTY': {
                    'near_expiry': '11NOV2025',
                    'expiry_date': datetime.date(2025, 11, 11),
                    'weekday': 1,
                    'weekday_name': 'Tuesday'
                },
                ...
            }

        Examples:
        ---------
        >>> # Fetch from Angel One
        >>> data = NSEExpiryEngine.fetch_expiries_from_angel_one()
        >>> print(data['NIFTY'])
        {'near_expiry': '11NOV2025', 'expiry_date': datetime.date(2025, 11, 11),
         'weekday': 1, 'weekday_name': 'Tuesday'}

        >>> # Update EXPIRY_DAYS mapping
        >>> new_mapping = {sym: info['weekday'] for sym, info in data.items()}
        >>> print(new_mapping)
        {'NIFTY': 1, 'BANKNIFTY': 1, 'FINNIFTY': 1, 'SENSEX': 3, 'MIDCPNIFTY': 1}
        """
        try:
            from SmartApi.smartConnect import SmartConnect
            import pyotp
            import requests
        except ImportError:
            raise ImportError(
                "Angel One dependencies not installed. Run: "
                "pip install smartapi-python pyotp requests"
            )

        # Load from env if not provided
        from dotenv import load_dotenv
        load_dotenv()

        api_key = api_key or os.getenv('ANGEL_API_KEY')
        client_id = client_id or os.getenv('ANGEL_CLIENT_ID')
        password = password or os.getenv('ANGEL_PASSWORD')
        totp_secret = totp_secret or os.getenv('ANGEL_TOTP_SECRET')

        if not all([api_key, client_id, password, totp_secret]):
            raise ValueError(
                "Angel One credentials not provided. Either pass them as arguments "
                "or set environment variables: ANGEL_API_KEY, ANGEL_CLIENT_ID, "
                "ANGEL_PASSWORD, ANGEL_TOTP_SECRET"
            )

        print("🔄 Connecting to Angel One API...")

        # Login
        smart_api = SmartConnect(api_key=api_key)
        totp = pyotp.TOTP(totp_secret)
        totp_code = totp.now()

        session = smart_api.generateSession(client_id, password, totp_code)
        print("✅ Connected to Angel One")

        # Fetch instruments
        print("📥 Fetching instrument master...")
        url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
        response = requests.get(url)
        instruments = response.json()
        df = pd.DataFrame(instruments)
        print(f"✅ Loaded {len(df):,} instruments")

        # Symbols to fetch
        symbols = ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'SENSEX', 'MIDCPNIFTY', 'BANKEX']

        results = {}
        weekday_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

        print("\n" + "="*80)
        print("FETCHING NEAR EXPIRIES FROM ANGEL ONE")
        print("="*80)

        for symbol in symbols:
            # Get options for this symbol
            opts = df[
                (df['name'] == symbol) &
                (df['instrumenttype'].isin(['OPTIDX', 'OPTSTK']))
            ]

            if opts.empty:
                print(f"\n⚠️  {symbol}: No data found")
                continue

            # Get unique expiries and sort
            expiries_raw = sorted(opts['expiry'].unique())

            if not expiries_raw:
                print(f"\n⚠️  {symbol}: No expiries found")
                continue

            # Parse first expiry (near expiry)
            near_expiry_raw = expiries_raw[0]

            try:
                # Try parsing DD MMM YY format (e.g., '11NOV25')
                expiry_date = pd.to_datetime(near_expiry_raw, format='%d%b%y', errors='coerce')

                if pd.isna(expiry_date):
                    # Try DD MMM YYYY format (e.g., '11NOV2025')
                    expiry_date = pd.to_datetime(near_expiry_raw, format='%d%b%Y', errors='coerce')

                if pd.isna(expiry_date):
                    print(f"\n⚠️  {symbol}: Could not parse expiry '{near_expiry_raw}'")
                    continue

                # Convert to date
                expiry_date = expiry_date.date()

                # Get weekday (0=Monday, 1=Tuesday, etc.)
                weekday = expiry_date.weekday()
                weekday_name = weekday_names[weekday]

                results[symbol] = {
                    'near_expiry': near_expiry_raw,
                    'expiry_date': expiry_date,
                    'weekday': weekday,
                    'weekday_name': weekday_name,
                    'total_options': len(opts),
                    'total_expiries': len(expiries_raw)
                }

                print(f"\n✅ {symbol}:")
                print(f"   Near Expiry: {near_expiry_raw}")
                print(f"   Date: {expiry_date.strftime('%d %b %Y')}")
                print(f"   Weekday: {weekday_name} ({weekday})")
                print(f"   Options: {len(opts):,}")

            except Exception as e:
                print(f"\n❌ {symbol}: Error parsing expiry - {e}")
                continue

        # Logout
        smart_api.terminateSession(client_id)
        print("\n" + "="*80)
        print("✅ FETCH COMPLETE")
        print("="*80)

        return results

    @classmethod
    def update_expiry_days_from_angel_one(cls, api_key: str = None, client_id: str = None,
                                          password: str = None, totp_secret: str = None,
                                          auto_update: bool = False) -> Dict[str, int]:
        """
        METHOD 2: Fetch from Angel One and generate new EXPIRY_DAYS mapping

        Parameters:
        -----------
        api_key, client_id, password, totp_secret : str
            Angel One credentials (optional, reads from env)
        auto_update : bool
            If True, automatically updates the class variable EXPIRY_DAYS
            If False, just returns the new mapping for review

        Returns:
        --------
        Dict[str, int] : New EXPIRY_DAYS mapping

        Examples:
        ---------
        >>> # Fetch and review (don't auto-update)
        >>> new_mapping = NSEExpiryEngine.update_expiry_days_from_angel_one()
        >>> print(new_mapping)
        {'NIFTY': 1, 'BANKNIFTY': 1, ...}

        >>> # Fetch and auto-update
        >>> NSEExpiryEngine.update_expiry_days_from_angel_one(auto_update=True)
        """
        # Fetch data from Angel One
        data = cls.fetch_expiries_from_angel_one(api_key, client_id, password, totp_secret)

        # Generate new mapping
        new_mapping = {symbol: info['weekday'] for symbol, info in data.items()}

        print("\n" + "="*80)
        print("GENERATED EXPIRY_DAYS MAPPING")
        print("="*80)
        print("\nEXPIRY_DAYS = {")
        for symbol, info in data.items():
            print(f"    '{symbol}': {info['weekday']},  # {info['weekday_name']} (Verified: {info['expiry_date'].strftime('%d %b %Y')})")
        print("}")

        if auto_update:
            # Update class variable
            cls.EXPIRY_DAYS = new_mapping
            print("\n✅ EXPIRY_DAYS updated automatically")
        else:
            print("\n⚠️  Review the mapping above. To update, set auto_update=True")

        print("="*80)

        return new_mapping


class NSEHolidayCalendar:
    """
    NSE/BSE Holiday Calendar

    Includes:
    - Trading holidays
    - Weekends
    - Special trading hours
    """

    # NSE Holidays for 2025 (update yearly)
    HOLIDAYS_2025 = [
        date(2025, 1, 26),   # Republic Day
        date(2025, 3, 14),   # Holi
        date(2025, 3, 31),   # Id-Ul-Fitr
        date(2025, 4, 10),   # Mahavir Jayanti
        date(2025, 4, 14),   # Dr. Ambedkar Jayanti
        date(2025, 4, 18),   # Good Friday
        date(2025, 5, 1),    # Maharashtra Day
        date(2025, 6, 7),    # Id-Ul-Adha (Bakri Id)
        date(2025, 7, 6),    # Muharram
        date(2025, 8, 15),   # Independence Day
        date(2025, 8, 27),   # Ganesh Chaturthi
        date(2025, 10, 2),   # Gandhi Jayanti
        date(2025, 10, 22),  # Dussehra
        date(2025, 11, 1),   # Diwali Laxmi Pujan
        date(2025, 11, 5),   # Gurunanak Jayanti
        date(2025, 12, 25),  # Christmas
    ]

    # NSE Holidays for 2026 (preliminary)
    HOLIDAYS_2026 = [
        date(2026, 1, 26),   # Republic Day
        date(2026, 3, 3),    # Holi
        date(2026, 3, 21),   # Id-Ul-Fitr (tentative)
        date(2026, 4, 2),    # Mahavir Jayanti
        date(2026, 4, 14),   # Dr. Ambedkar Jayanti
        date(2026, 4, 3),    # Good Friday
        date(2026, 5, 1),    # Maharashtra Day
        date(2026, 5, 28),   # Id-Ul-Adha (tentative)
        date(2026, 6, 26),   # Muharram (tentative)
        date(2026, 8, 15),   # Independence Day
        date(2026, 9, 16),   # Ganesh Chaturthi
        date(2026, 10, 2),   # Gandhi Jayanti
        date(2026, 10, 11),  # Dussehra
        date(2026, 10, 19),  # Diwali Laxmi Pujan
        date(2026, 11, 24),  # Gurunanak Jayanti
        date(2026, 12, 25),  # Christmas
    ]

    def __init__(self):
        """Initialize Holiday Calendar"""
        self.holidays = set(self.HOLIDAYS_2025 + self.HOLIDAYS_2026)

    def is_holiday(self, check_date: date) -> bool:
        """
        Check if date is a holiday

        Parameters:
        -----------
        check_date : date
            Date to check

        Returns:
        --------
        bool : True if holiday (including weekends)
        """
        # Check weekend
        if check_date.weekday() in [5, 6]:  # Saturday, Sunday
            return True

        # Check trading holiday
        return check_date in self.holidays

    def is_trading_day(self, check_date: date) -> bool:
        """Check if date is a trading day"""
        return not self.is_holiday(check_date)

    def get_next_trading_day(self, from_date: Optional[date] = None) -> date:
        """
        Get next trading day

        Parameters:
        -----------
        from_date : date
            From date (default: today)

        Returns:
        --------
        date : Next trading day
        """
        if from_date is None:
            from_date = date.today()

        next_day = from_date + timedelta(days=1)

        while self.is_holiday(next_day):
            next_day += timedelta(days=1)

        return next_day

    def get_previous_trading_day(self, from_date: Optional[date] = None) -> date:
        """Get previous trading day"""
        if from_date is None:
            from_date = date.today()

        prev_day = from_date - timedelta(days=1)

        while self.is_holiday(prev_day):
            prev_day -= timedelta(days=1)

        return prev_day

    def get_trading_days_between(self, start_date: date, end_date: date) -> List[date]:
        """
        Get all trading days between two dates

        Parameters:
        -----------
        start_date : date
            Start date
        end_date : date
            End date

        Returns:
        --------
        List[date] : List of trading days
        """
        trading_days = []
        current = start_date

        while current <= end_date:
            if self.is_trading_day(current):
                trading_days.append(current)
            current += timedelta(days=1)

        return trading_days

    def count_trading_days(self, start_date: date, end_date: date) -> int:
        """Count trading days between two dates"""
        return len(self.get_trading_days_between(start_date, end_date))

    def add_trading_days(self, from_date: date, num_days: int) -> date:
        """
        Add N trading days to a date

        Parameters:
        -----------
        from_date : date
            Start date
        num_days : int
            Number of trading days to add

        Returns:
        --------
        date : Date after adding N trading days
        """
        current = from_date
        days_added = 0

        while days_added < num_days:
            current = self.get_next_trading_day(current)
            days_added += 1

        return current

    def get_month_holidays(self, year: int, month: int) -> List[date]:
        """Get all holidays in a month"""
        first_day = date(year, month, 1)
        last_day = date(year, month, calendar.monthrange(year, month)[1])

        month_holidays = []
        current = first_day

        while current <= last_day:
            if self.is_holiday(current):
                month_holidays.append(current)
            current += timedelta(days=1)

        return month_holidays

    def add_custom_holiday(self, holiday_date: date) -> None:
        """Add custom holiday to calendar"""
        self.holidays.add(holiday_date)

    def remove_holiday(self, holiday_date: date) -> None:
        """Remove holiday from calendar"""
        self.holidays.discard(holiday_date)

    def __repr__(self) -> str:
        return f"<NSEHolidayCalendar: {len(self.holidays)} holidays>"


# ==================== USAGE EXAMPLES ====================

if __name__ == "__main__":
    # Initialize
    calendar_obj = NSEHolidayCalendar()
    expiry_engine = NSEExpiryEngine(holiday_calendar=calendar_obj)

    print("=" * 80)
    print("NSE EXPIRY ENGINE - EXAMPLES")
    print("=" * 80)

    # Example 1: Next Nifty expiry
    print("\n1. Next Nifty Weekly Expiry:")
    nifty_expiry = expiry_engine.get_next_expiry('NIFTY', weekly=True)
    print(f"   Date: {nifty_expiry.strftime('%d-%b-%Y (%A)')}")
    print(f"   Days to expiry: {expiry_engine.days_to_expiry('NIFTY')}")

    # Example 2: Nifty monthly expiry
    print("\n2. Next Nifty Monthly Expiry:")
    nifty_monthly = expiry_engine.get_next_expiry('NIFTY', weekly=False)
    print(f"   Date: {nifty_monthly.strftime('%d-%b-%Y (%A)')}")

    # Example 3: Bank Nifty expiries
    print("\n3. Bank Nifty Next 4 Weekly Expiries:")
    bn_expiries = expiry_engine.get_all_expiries('BANKNIFTY', count=4)
    for i, exp in enumerate(bn_expiries, 1):
        print(f"   {i}. {exp.strftime('%d-%b-%Y (%A)')}")

    # Example 4: All symbols
    print("\n4. Next Expiry for All Symbols:")
    for symbol in expiry_engine.EXPIRY_DAYS.keys():
        try:
            exp = expiry_engine.get_next_expiry(symbol)
            days = expiry_engine.days_to_expiry(symbol)
            print(f"   {symbol:12s}: {exp.strftime('%d-%b-%Y')} ({days:2d} days)")
        except:
            pass

    # Example 5: Check if today is expiry
    print("\n5. Is Today an Expiry Day?")
    today = date.today()
    for symbol in ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'SENSEX']:
        is_expiry = expiry_engine.is_expiry_day(today, symbol)
        print(f"   {symbol:12s}: {'YES ✓' if is_expiry else 'NO'}")

    # Example 6: Time to expiry (for options pricing)
    print("\n6. Time to Expiry (for pricing):")
    for symbol in ['NIFTY', 'BANKNIFTY']:
        T = expiry_engine.time_to_expiry(symbol)
        print(f"   {symbol:12s}: {T:.4f} years ({T*365:.1f} days)")

    # Example 7: Expiry series
    print("\n7. Nifty Expiry Series (Current, Next, Far):")
    current, next_exp, far = expiry_engine.get_expiry_series('NIFTY')
    print(f"   Current: {current.strftime('%d-%b-%Y')}")
    print(f"   Next:    {next_exp.strftime('%d-%b-%Y')}")
    print(f"   Far:     {far.strftime('%d-%b-%Y')}")

    # Example 8: Holiday calendar
    print("\n8. Holiday Calendar:")
    print(f"   Total holidays: {len(calendar_obj.holidays)}")
    print(f"   Is today a holiday? {'YES' if calendar_obj.is_holiday(today) else 'NO'}")
    print(f"   Is today a trading day? {'YES' if calendar_obj.is_trading_day(today) else 'NO'}")

    next_trading = calendar_obj.get_next_trading_day()
    print(f"   Next trading day: {next_trading.strftime('%d-%b-%Y (%A)')}")

    # Example 9: Trading days this month
    print("\n9. November 2025 Trading Days:")
    trading_days = calendar_obj.get_trading_days_between(
        date(2025, 11, 1),
        date(2025, 11, 30)
    )
    print(f"   Total trading days: {len(trading_days)}")

    print("\n" + "=" * 80)
