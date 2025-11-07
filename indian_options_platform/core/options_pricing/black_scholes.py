"""
Black-Scholes Options Pricing Model
Supports both European Call and Put options
Optimized for Indian market (NSE/BSE)
"""

import numpy as np
from scipy.stats import norm
from typing import Union, Tuple
import warnings


class BlackScholes:
    """
    Black-Scholes Options Pricing Model

    Formula:
    Call = S * N(d1) - K * e^(-r*T) * N(d2)
    Put = K * e^(-r*T) * N(-d2) - S * N(-d1)

    where:
    d1 = [ln(S/K) + (r + σ²/2)*T] / (σ*√T)
    d2 = d1 - σ*√T
    """

    def __init__(self):
        self.model_name = "Black-Scholes-Merton"

    @staticmethod
    def _validate_inputs(S: float, K: float, T: float, r: float, sigma: float) -> None:
        """Validate input parameters"""
        if S <= 0:
            raise ValueError(f"Spot price must be positive, got {S}")
        if K <= 0:
            raise ValueError(f"Strike price must be positive, got {K}")
        if T < 0:
            raise ValueError(f"Time to expiry cannot be negative, got {T}")
        if sigma < 0:
            raise ValueError(f"Volatility cannot be negative, got {sigma}")
        if T == 0:
            warnings.warn("Time to expiry is 0, returning intrinsic value")

    @staticmethod
    def _d1(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """Calculate d1 parameter"""
        if T == 0:
            return np.inf if S > K else -np.inf
        return (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))

    @staticmethod
    def _d2(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """Calculate d2 parameter"""
        if T == 0:
            return np.inf if S > K else -np.inf
        d1 = BlackScholes._d1(S, K, T, r, sigma)
        return d1 - sigma * np.sqrt(T)

    def call_price(self, S: float, K: float, T: float, r: float, sigma: float) -> float:
        """
        Calculate European Call Option Price

        Parameters:
        -----------
        S : float
            Current spot price of underlying
        K : float
            Strike price
        T : float
            Time to expiration (in years)
        r : float
            Risk-free interest rate (annual)
        sigma : float
            Volatility (annual)

        Returns:
        --------
        float : Call option price
        """
        self._validate_inputs(S, K, T, r, sigma)

        # Handle expiry (T=0)
        if T == 0:
            return max(0, S - K)

        d1 = self._d1(S, K, T, r, sigma)
        d2 = self._d2(S, K, T, r, sigma)

        call = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        return max(0, call)  # Ensure non-negative price

    def put_price(self, S: float, K: float, T: float, r: float, sigma: float) -> float:
        """
        Calculate European Put Option Price

        Parameters:
        -----------
        S : float
            Current spot price of underlying
        K : float
            Strike price
        T : float
            Time to expiration (in years)
        r : float
            Risk-free interest rate (annual)
        sigma : float
            Volatility (annual)

        Returns:
        --------
        float : Put option price
        """
        self._validate_inputs(S, K, T, r, sigma)

        # Handle expiry (T=0)
        if T == 0:
            return max(0, K - S)

        d1 = self._d1(S, K, T, r, sigma)
        d2 = self._d2(S, K, T, r, sigma)

        put = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        return max(0, put)  # Ensure non-negative price

    def option_price(self, S: float, K: float, T: float, r: float, sigma: float,
                    option_type: str = 'call') -> float:
        """
        Calculate option price (call or put)

        Parameters:
        -----------
        option_type : str
            'call' or 'put'
        """
        option_type = option_type.lower()
        if option_type == 'call':
            return self.call_price(S, K, T, r, sigma)
        elif option_type == 'put':
            return self.put_price(S, K, T, r, sigma)
        else:
            raise ValueError(f"option_type must be 'call' or 'put', got {option_type}")

    def intrinsic_value(self, S: float, K: float, option_type: str = 'call') -> float:
        """Calculate intrinsic value of option"""
        if option_type.lower() == 'call':
            return max(0, S - K)
        elif option_type.lower() == 'put':
            return max(0, K - S)
        else:
            raise ValueError(f"option_type must be 'call' or 'put'")

    def time_value(self, S: float, K: float, T: float, r: float, sigma: float,
                  option_type: str = 'call') -> float:
        """Calculate time value of option"""
        option_price = self.option_price(S, K, T, r, sigma, option_type)
        intrinsic = self.intrinsic_value(S, K, option_type)
        return option_price - intrinsic

    def moneyness(self, S: float, K: float) -> Tuple[str, float]:
        """
        Determine option moneyness

        Returns:
        --------
        Tuple[str, float] : (moneyness_type, percentage)
            moneyness_type: 'ITM', 'ATM', or 'OTM'
            percentage: how far in/out of money (as %)
        """
        ratio = S / K
        pct = (ratio - 1) * 100

        if abs(pct) < 0.5:  # Within 0.5%
            return 'ATM', pct
        elif ratio > 1:
            return 'ITM', pct  # For calls
        else:
            return 'OTM', pct  # For calls

    def put_call_parity_check(self, call_price: float, put_price: float,
                              S: float, K: float, T: float, r: float) -> float:
        """
        Check Put-Call Parity: C - P = S - K*e^(-r*T)

        Returns:
        --------
        float : Arbitrage profit (should be near 0)
        """
        theoretical_diff = S - K * np.exp(-r * T)
        actual_diff = call_price - put_price
        return actual_diff - theoretical_diff


# Vectorized version for bulk calculations
class BlackScholesVectorized(BlackScholes):
    """
    Vectorized Black-Scholes for bulk option pricing
    Useful for options chain calculations
    """

    def call_price_vectorized(self, S: Union[float, np.ndarray],
                             K: Union[float, np.ndarray],
                             T: Union[float, np.ndarray],
                             r: Union[float, np.ndarray],
                             sigma: Union[float, np.ndarray]) -> np.ndarray:
        """Vectorized call price calculation"""
        S, K, T, r, sigma = map(np.asarray, [S, K, T, r, sigma])

        # Handle T=0 cases
        mask_zero = (T == 0)
        result = np.zeros_like(S, dtype=float)

        # Non-zero T
        mask_nonzero = ~mask_zero
        if np.any(mask_nonzero):
            S_nz = S[mask_nonzero] if S.shape else S
            K_nz = K[mask_nonzero] if K.shape else K
            T_nz = T[mask_nonzero] if T.shape else T
            r_nz = r[mask_nonzero] if r.shape else r
            sigma_nz = sigma[mask_nonzero] if sigma.shape else sigma

            d1 = (np.log(S_nz / K_nz) + (r_nz + 0.5 * sigma_nz ** 2) * T_nz) / (sigma_nz * np.sqrt(T_nz))
            d2 = d1 - sigma_nz * np.sqrt(T_nz)

            call = S_nz * norm.cdf(d1) - K_nz * np.exp(-r_nz * T_nz) * norm.cdf(d2)
            result[mask_nonzero] = call

        # T=0 cases: intrinsic value
        if np.any(mask_zero):
            S_z = S[mask_zero] if S.shape else S
            K_z = K[mask_zero] if K.shape else K
            result[mask_zero] = np.maximum(0, S_z - K_z)

        return np.maximum(0, result)

    def put_price_vectorized(self, S: Union[float, np.ndarray],
                            K: Union[float, np.ndarray],
                            T: Union[float, np.ndarray],
                            r: Union[float, np.ndarray],
                            sigma: Union[float, np.ndarray]) -> np.ndarray:
        """Vectorized put price calculation"""
        S, K, T, r, sigma = map(np.asarray, [S, K, T, r, sigma])

        # Handle T=0 cases
        mask_zero = (T == 0)
        result = np.zeros_like(S, dtype=float)

        # Non-zero T
        mask_nonzero = ~mask_zero
        if np.any(mask_nonzero):
            S_nz = S[mask_nonzero] if S.shape else S
            K_nz = K[mask_nonzero] if K.shape else K
            T_nz = T[mask_nonzero] if T.shape else T
            r_nz = r[mask_nonzero] if r.shape else r
            sigma_nz = sigma[mask_nonzero] if sigma.shape else sigma

            d1 = (np.log(S_nz / K_nz) + (r_nz + 0.5 * sigma_nz ** 2) * T_nz) / (sigma_nz * np.sqrt(T_nz))
            d2 = d1 - sigma_nz * np.sqrt(T_nz)

            put = K_nz * np.exp(-r_nz * T_nz) * norm.cdf(-d2) - S_nz * norm.cdf(-d1)
            result[mask_nonzero] = put

        # T=0 cases: intrinsic value
        if np.any(mask_zero):
            S_z = S[mask_zero] if S.shape else S
            K_z = K[mask_zero] if K.shape else K
            result[mask_zero] = np.maximum(0, K_z - S_z)

        return np.maximum(0, result)


if __name__ == "__main__":
    # Example usage for Indian market
    bs = BlackScholes()

    # Nifty example
    spot = 19500  # Nifty spot
    strike = 19500  # ATM strike
    days_to_expiry = 7  # Weekly expiry
    T = days_to_expiry / 365
    r = 0.07  # 7% risk-free rate (approximate Indian T-bill rate)
    sigma = 0.15  # 15% annual volatility

    call = bs.call_price(spot, strike, T, r, sigma)
    put = bs.put_price(spot, strike, T, r, sigma)

    print(f"Nifty Spot: {spot}")
    print(f"Strike: {strike}")
    print(f"Days to Expiry: {days_to_expiry}")
    print(f"Call Price: ₹{call:.2f}")
    print(f"Put Price: ₹{put:.2f}")
    print(f"Moneyness: {bs.moneyness(spot, strike)}")
