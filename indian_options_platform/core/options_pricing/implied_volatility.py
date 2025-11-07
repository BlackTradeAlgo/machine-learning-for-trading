"""
Implied Volatility Calculator
Uses Newton-Raphson method for fast convergence
"""

import numpy as np
from scipy.optimize import brentq, newton
from typing import Optional, Union
from .black_scholes import BlackScholes
from .greeks import Greeks


class ImpliedVolatility:
    """
    Calculate Implied Volatility from option market prices

    Methods:
    --------
    1. Newton-Raphson (fast, may fail for extreme cases)
    2. Brent's method (robust, slightly slower)
    3. Bisection (fallback, always converges)
    """

    def __init__(self):
        self.bs = BlackScholes()
        self.greeks = Greeks()

    def newton_raphson(self, market_price: float, S: float, K: float, T: float,
                      r: float, option_type: str = 'call',
                      initial_vol: float = 0.3, max_iterations: int = 100,
                      tolerance: float = 1e-6) -> Optional[float]:
        """
        Newton-Raphson method for IV calculation

        Uses Vega as the derivative
        Faster but may fail for extreme cases

        Formula: σ_new = σ_old - (V(σ) - V_market) / Vega(σ)
        """
        if T <= 0:
            return None

        sigma = initial_vol

        for i in range(max_iterations):
            # Calculate option price with current volatility
            if option_type.lower() == 'call':
                price = self.bs.call_price(S, K, T, r, sigma)
            else:
                price = self.bs.put_price(S, K, T, r, sigma)

            # Calculate price difference
            diff = price - market_price

            # Check convergence
            if abs(diff) < tolerance:
                return sigma

            # Calculate Vega
            vega = self.greeks.vega(S, K, T, r, sigma)

            # Avoid division by zero
            if abs(vega) < 1e-10:
                return None

            # Newton-Raphson update
            sigma = sigma - diff / (vega * 100)  # vega is per 1%

            # Ensure sigma stays positive and reasonable
            sigma = max(0.001, min(5.0, sigma))

        # Did not converge
        return None

    def brent_method(self, market_price: float, S: float, K: float, T: float,
                    r: float, option_type: str = 'call',
                    vol_min: float = 0.001, vol_max: float = 5.0) -> Optional[float]:
        """
        Brent's method for IV calculation

        More robust than Newton-Raphson
        Always converges if solution exists in [vol_min, vol_max]
        """
        if T <= 0:
            return None

        def objective(sigma):
            if option_type.lower() == 'call':
                price = self.bs.call_price(S, K, T, r, sigma)
            else:
                price = self.bs.put_price(S, K, T, r, sigma)
            return price - market_price

        try:
            # Check if solution exists in range
            f_min = objective(vol_min)
            f_max = objective(vol_max)

            if f_min * f_max > 0:
                # No sign change, solution may not exist in range
                return None

            iv = brentq(objective, vol_min, vol_max, xtol=1e-6, maxiter=100)
            return iv

        except Exception:
            return None

    def bisection(self, market_price: float, S: float, K: float, T: float,
                 r: float, option_type: str = 'call',
                 vol_min: float = 0.001, vol_max: float = 5.0,
                 tolerance: float = 1e-6, max_iterations: int = 100) -> Optional[float]:
        """
        Bisection method for IV calculation

        Slowest but most robust
        Guaranteed to converge if solution exists
        """
        if T <= 0:
            return None

        def objective(sigma):
            if option_type.lower() == 'call':
                price = self.bs.call_price(S, K, T, r, sigma)
            else:
                price = self.bs.put_price(S, K, T, r, sigma)
            return price - market_price

        a, b = vol_min, vol_max
        f_a = objective(a)
        f_b = objective(b)

        # Check if solution exists
        if f_a * f_b > 0:
            return None

        for i in range(max_iterations):
            c = (a + b) / 2
            f_c = objective(c)

            if abs(f_c) < tolerance or (b - a) / 2 < tolerance:
                return c

            if f_a * f_c < 0:
                b = c
                f_b = f_c
            else:
                a = c
                f_a = f_c

        return (a + b) / 2

    def calculate(self, market_price: float, S: float, K: float, T: float,
                 r: float, option_type: str = 'call',
                 method: str = 'newton') -> Optional[float]:
        """
        Calculate IV using specified method

        Parameters:
        -----------
        method : str
            'newton', 'brent', or 'bisection'

        Returns:
        --------
        float or None : Implied volatility (annual)
        """
        # Quick checks
        intrinsic = max(0, S - K) if option_type.lower() == 'call' else max(0, K - S)

        if market_price < intrinsic:
            # Price below intrinsic value - invalid
            return None

        if T <= 0:
            return None

        method = method.lower()

        if method == 'newton':
            iv = self.newton_raphson(market_price, S, K, T, r, option_type)
        elif method == 'brent':
            iv = self.brent_method(market_price, S, K, T, r, option_type)
        elif method == 'bisection':
            iv = self.bisection(market_price, S, K, T, r, option_type)
        else:
            raise ValueError(f"Unknown method: {method}")

        # If Newton-Raphson failed, fallback to Brent
        if iv is None and method == 'newton':
            iv = self.brent_method(market_price, S, K, T, r, option_type)

        return iv

    def iv_surface(self, option_chain: dict, S: float, T: float, r: float,
                  method: str = 'newton') -> dict:
        """
        Calculate IV surface from options chain

        Parameters:
        -----------
        option_chain : dict
            Format: {strike: {'call_price': float, 'put_price': float}}

        Returns:
        --------
        dict : {strike: {'call_iv': float, 'put_iv': float}}
        """
        iv_surface = {}

        for strike, prices in option_chain.items():
            iv_surface[strike] = {}

            if 'call_price' in prices and prices['call_price'] is not None:
                call_iv = self.calculate(prices['call_price'], S, strike, T, r, 'call', method)
                iv_surface[strike]['call_iv'] = call_iv

            if 'put_price' in prices and prices['put_price'] is not None:
                put_iv = self.calculate(prices['put_price'], S, strike, T, r, 'put', method)
                iv_surface[strike]['put_iv'] = put_iv

        return iv_surface

    def iv_smile(self, strikes: list, option_prices: list, S: float, T: float,
                r: float, option_type: str = 'call', method: str = 'newton') -> np.ndarray:
        """
        Calculate IV smile/skew

        Returns:
        --------
        np.ndarray : Array of implied volatilities
        """
        ivs = []

        for strike, price in zip(strikes, option_prices):
            iv = self.calculate(price, S, strike, T, r, option_type, method)
            ivs.append(iv if iv is not None else np.nan)

        return np.array(ivs)

    def iv_percentile(self, current_iv: float, historical_ivs: list,
                     period: int = 252) -> float:
        """
        Calculate IV percentile (IV Rank)

        Shows where current IV stands relative to historical range

        Returns:
        --------
        float : Percentile (0-100)
        """
        if len(historical_ivs) < 2:
            return 50.0

        historical_ivs = np.array(historical_ivs[-period:])
        percentile = (np.sum(historical_ivs < current_iv) / len(historical_ivs)) * 100

        return percentile

    def iv_rank(self, current_iv: float, historical_ivs: list,
               period: int = 252) -> float:
        """
        Calculate IV Rank

        (Current IV - Min IV) / (Max IV - Min IV) * 100

        Returns:
        --------
        float : IV Rank (0-100)
        """
        if len(historical_ivs) < 2:
            return 50.0

        historical_ivs = np.array(historical_ivs[-period:])
        min_iv = np.min(historical_ivs)
        max_iv = np.max(historical_ivs)

        if max_iv == min_iv:
            return 50.0

        iv_rank = ((current_iv - min_iv) / (max_iv - min_iv)) * 100

        return iv_rank

    def atm_iv(self, option_chain: dict, spot: float) -> tuple:
        """
        Get ATM implied volatility

        Returns:
        --------
        tuple : (atm_strike, call_iv, put_iv)
        """
        # Find ATM strike (closest to spot)
        strikes = list(option_chain.keys())
        atm_strike = min(strikes, key=lambda x: abs(x - spot))

        call_iv = option_chain[atm_strike].get('call_iv', None)
        put_iv = option_chain[atm_strike].get('put_iv', None)

        return atm_strike, call_iv, put_iv


# Vectorized IV calculation
class ImpliedVolatilityVectorized(ImpliedVolatility):
    """
    Vectorized IV calculation for options chains
    Much faster for bulk calculations
    """

    def calculate_vectorized(self, market_prices: np.ndarray,
                            S: Union[float, np.ndarray],
                            K: Union[float, np.ndarray],
                            T: Union[float, np.ndarray],
                            r: Union[float, np.ndarray],
                            option_type: str = 'call',
                            initial_vol: float = 0.3,
                            max_iterations: int = 50,
                            tolerance: float = 1e-6) -> np.ndarray:
        """
        Vectorized Newton-Raphson IV calculation

        Much faster for calculating IV for entire options chain
        """
        market_prices = np.asarray(market_prices)
        S = np.asarray(S)
        K = np.asarray(K)
        T = np.asarray(T)
        r = np.asarray(r)

        sigma = np.full_like(market_prices, initial_vol, dtype=float)
        converged = np.zeros_like(market_prices, dtype=bool)

        for i in range(max_iterations):
            # Calculate prices
            if option_type.lower() == 'call':
                d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
                d2 = d1 - sigma * np.sqrt(T)
                from scipy.stats import norm
                prices = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
            else:
                d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
                d2 = d1 - sigma * np.sqrt(T)
                from scipy.stats import norm
                prices = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

            # Calculate difference
            diff = prices - market_prices

            # Check convergence
            converged = converged | (np.abs(diff) < tolerance)

            if np.all(converged):
                break

            # Calculate Vega
            vega = S * norm.pdf(d1) * np.sqrt(T) / 100

            # Update sigma
            sigma = sigma - diff / (vega * 100)

            # Ensure bounds
            sigma = np.clip(sigma, 0.001, 5.0)

        # Set non-converged to NaN
        sigma[~converged] = np.nan

        return sigma


if __name__ == "__main__":
    # Example: Calculate IV for Nifty option
    iv_calc = ImpliedVolatility()

    S = 19500  # Nifty spot
    K = 19500  # ATM strike
    T = 7 / 365  # 7 days
    r = 0.07  # 7% rate
    market_price = 150  # Market price of call option

    print("=" * 60)
    print("Implied Volatility Calculation - Nifty 19500 CE")
    print("=" * 60)
    print(f"Spot: ₹{S}")
    print(f"Strike: ₹{K}")
    print(f"Days to Expiry: 7")
    print(f"Market Price: ₹{market_price}")
    print()

    # Try all methods
    methods = ['newton', 'brent', 'bisection']

    for method in methods:
        iv = iv_calc.calculate(market_price, S, K, T, r, 'call', method)
        if iv:
            print(f"{method.capitalize():12s} Method: {iv*100:.2f}% (σ = {iv:.4f})")
        else:
            print(f"{method.capitalize():12s} Method: Failed to converge")

    # IV Smile example
    print("\n" + "=" * 60)
    print("IV Smile - Nifty Options Chain")
    print("=" * 60)

    strikes = [19000, 19200, 19400, 19500, 19600, 19800, 20000]
    call_prices = [520, 330, 180, 150, 100, 40, 15]

    ivs = iv_calc.iv_smile(strikes, call_prices, S, T, r, 'call')

    print(f"{'Strike':<10} {'Price':<10} {'IV (%)':<10}")
    print("-" * 30)
    for strike, price, iv in zip(strikes, call_prices, ivs):
        if not np.isnan(iv):
            print(f"{strike:<10} ₹{price:<9} {iv*100:<10.2f}")
        else:
            print(f"{strike:<10} ₹{price:<9} {'N/A':<10}")

    # IV Percentile example
    print("\n" + "=" * 60)
    print("IV Percentile & Rank")
    print("=" * 60)

    current_iv = 0.15
    historical_ivs = np.random.uniform(0.10, 0.25, 252).tolist()  # Simulated

    iv_pct = iv_calc.iv_percentile(current_iv, historical_ivs)
    iv_rnk = iv_calc.iv_rank(current_iv, historical_ivs)

    print(f"Current IV: {current_iv*100:.2f}%")
    print(f"IV Percentile: {iv_pct:.1f}%")
    print(f"IV Rank: {iv_rnk:.1f}%")

    if iv_pct > 70:
        print("→ High IV environment (Good for selling premium)")
    elif iv_pct < 30:
        print("→ Low IV environment (Good for buying options)")
    else:
        print("→ Moderate IV environment")
