"""
Greeks Calculation Module
Calculates all first and second-order Greeks for options
"""

import numpy as np
from scipy.stats import norm
from typing import Dict, Union
from .black_scholes import BlackScholes


class Greeks:
    """
    Calculate Option Greeks (sensitivities)

    First-order Greeks:
    - Delta: ∂V/∂S (price sensitivity)
    - Gamma: ∂²V/∂S² (delta sensitivity)
    - Vega: ∂V/∂σ (volatility sensitivity)
    - Theta: ∂V/∂T (time decay)
    - Rho: ∂V/∂r (interest rate sensitivity)

    Second-order Greeks:
    - Vanna: ∂²V/∂S∂σ
    - Charm: ∂²V/∂S∂T
    - Vomma: ∂²V/∂σ²
    - Vera: ∂²V/∂σ∂r
    """

    def __init__(self):
        self.bs = BlackScholes()

    @staticmethod
    def _d1(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """Calculate d1 parameter"""
        if T == 0:
            return np.inf if S > K else -np.inf
        return (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))

    @staticmethod
    def _d2(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """Calculate d2 parameter"""
        d1 = Greeks._d1(S, K, T, r, sigma)
        if T == 0:
            return d1
        return d1 - sigma * np.sqrt(T)

    # ==================== FIRST ORDER GREEKS ====================

    def delta(self, S: float, K: float, T: float, r: float, sigma: float,
             option_type: str = 'call') -> float:
        """
        Calculate Delta (∂V/∂S)

        Call Delta: N(d1)
        Put Delta: N(d1) - 1

        Range: Call [0, 1], Put [-1, 0]
        """
        if T == 0:
            if option_type.lower() == 'call':
                return 1.0 if S > K else 0.0
            else:
                return -1.0 if S < K else 0.0

        d1 = self._d1(S, K, T, r, sigma)

        if option_type.lower() == 'call':
            return norm.cdf(d1)
        elif option_type.lower() == 'put':
            return norm.cdf(d1) - 1
        else:
            raise ValueError("option_type must be 'call' or 'put'")

    def gamma(self, S: float, K: float, T: float, r: float, sigma: float) -> float:
        """
        Calculate Gamma (∂²V/∂S²)

        Gamma = N'(d1) / (S * σ * √T)

        Same for both call and put
        Always positive
        """
        if T == 0:
            return 0.0

        d1 = self._d1(S, K, T, r, sigma)
        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
        return gamma

    def vega(self, S: float, K: float, T: float, r: float, sigma: float) -> float:
        """
        Calculate Vega (∂V/∂σ)

        Vega = S * N'(d1) * √T

        Same for both call and put
        Usually expressed per 1% change in volatility
        """
        if T == 0:
            return 0.0

        d1 = self._d1(S, K, T, r, sigma)
        vega = S * norm.pdf(d1) * np.sqrt(T)
        return vega / 100  # Per 1% change in volatility

    def theta(self, S: float, K: float, T: float, r: float, sigma: float,
             option_type: str = 'call') -> float:
        """
        Calculate Theta (∂V/∂T)

        Time decay - usually negative
        Expressed per day (divide by 365)
        """
        if T == 0:
            return 0.0

        d1 = self._d1(S, K, T, r, sigma)
        d2 = self._d2(S, K, T, r, sigma)

        if option_type.lower() == 'call':
            theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T))
                    - r * K * np.exp(-r * T) * norm.cdf(d2))
        elif option_type.lower() == 'put':
            theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T))
                    + r * K * np.exp(-r * T) * norm.cdf(-d2))
        else:
            raise ValueError("option_type must be 'call' or 'put'")

        return theta / 365  # Per day

    def rho(self, S: float, K: float, T: float, r: float, sigma: float,
           option_type: str = 'call') -> float:
        """
        Calculate Rho (∂V/∂r)

        Interest rate sensitivity
        Usually less important for short-dated options
        Expressed per 1% change in interest rate
        """
        if T == 0:
            return 0.0

        d2 = self._d2(S, K, T, r, sigma)

        if option_type.lower() == 'call':
            rho = K * T * np.exp(-r * T) * norm.cdf(d2)
        elif option_type.lower() == 'put':
            rho = -K * T * np.exp(-r * T) * norm.cdf(-d2)
        else:
            raise ValueError("option_type must be 'call' or 'put'")

        return rho / 100  # Per 1% change in rate

    # ==================== SECOND ORDER GREEKS ====================

    def vanna(self, S: float, K: float, T: float, r: float, sigma: float) -> float:
        """
        Calculate Vanna (∂²V/∂S∂σ) = ∂Delta/∂σ = ∂Vega/∂S

        Sensitivity of delta to volatility changes
        """
        if T == 0:
            return 0.0

        d1 = self._d1(S, K, T, r, sigma)
        d2 = self._d2(S, K, T, r, sigma)

        vanna = -norm.pdf(d1) * d2 / sigma
        return vanna / 100  # Per 1% volatility change

    def charm(self, S: float, K: float, T: float, r: float, sigma: float,
             option_type: str = 'call') -> float:
        """
        Calculate Charm (∂²V/∂S∂T) = ∂Delta/∂T

        Rate of change of delta over time
        Also called "delta decay"
        """
        if T == 0:
            return 0.0

        d1 = self._d1(S, K, T, r, sigma)
        d2 = self._d2(S, K, T, r, sigma)

        if option_type.lower() == 'call':
            charm = -norm.pdf(d1) * (2 * r * T - d2 * sigma * np.sqrt(T)) / (2 * T * sigma * np.sqrt(T))
        elif option_type.lower() == 'put':
            charm = -norm.pdf(d1) * (2 * r * T - d2 * sigma * np.sqrt(T)) / (2 * T * sigma * np.sqrt(T))
        else:
            raise ValueError("option_type must be 'call' or 'put'")

        return charm / 365  # Per day

    def vomma(self, S: float, K: float, T: float, r: float, sigma: float) -> float:
        """
        Calculate Vomma (∂²V/∂σ²) = ∂Vega/∂σ

        Sensitivity of vega to volatility changes
        Also called "Volga"
        """
        if T == 0:
            return 0.0

        d1 = self._d1(S, K, T, r, sigma)
        d2 = self._d2(S, K, T, r, sigma)

        vomma = S * norm.pdf(d1) * np.sqrt(T) * d1 * d2 / sigma
        return vomma / 10000  # Per 1% change squared

    def vera(self, S: float, K: float, T: float, r: float, sigma: float) -> float:
        """
        Calculate Vera (∂²V/∂σ∂r) = ∂Vega/∂r

        Sensitivity of vega to interest rate changes
        Also called "Rhova"
        """
        if T == 0:
            return 0.0

        d1 = self._d1(S, K, T, r, sigma)
        d2 = self._d2(S, K, T, r, sigma)

        vera = K * T * np.exp(-r * T) * norm.pdf(d2) * np.sqrt(T) * d1 / sigma
        return vera / 10000  # Per 1% change in both

    # ==================== UTILITY METHODS ====================

    def all_greeks(self, S: float, K: float, T: float, r: float, sigma: float,
                  option_type: str = 'call') -> Dict[str, float]:
        """
        Calculate all Greeks at once

        Returns:
        --------
        Dict with all Greek values
        """
        greeks = {
            'delta': self.delta(S, K, T, r, sigma, option_type),
            'gamma': self.gamma(S, K, T, r, sigma),
            'vega': self.vega(S, K, T, r, sigma),
            'theta': self.theta(S, K, T, r, sigma, option_type),
            'rho': self.rho(S, K, T, r, sigma, option_type),
            'vanna': self.vanna(S, K, T, r, sigma),
            'charm': self.charm(S, K, T, r, sigma, option_type),
            'vomma': self.vomma(S, K, T, r, sigma),
            'vera': self.vera(S, K, T, r, sigma)
        }
        return greeks

    def portfolio_greeks(self, positions: list) -> Dict[str, float]:
        """
        Calculate portfolio-level Greeks

        Parameters:
        -----------
        positions : list of dict
            Each dict should contain:
            {
                'S': spot price,
                'K': strike,
                'T': time to expiry,
                'r': risk-free rate,
                'sigma': volatility,
                'option_type': 'call' or 'put',
                'quantity': number of contracts,
                'lot_size': lot size
            }

        Returns:
        --------
        Dict with aggregated Greeks
        """
        portfolio = {
            'delta': 0.0,
            'gamma': 0.0,
            'vega': 0.0,
            'theta': 0.0,
            'rho': 0.0,
            'vanna': 0.0,
            'charm': 0.0,
            'vomma': 0.0,
            'vera': 0.0
        }

        for pos in positions:
            greeks = self.all_greeks(
                pos['S'], pos['K'], pos['T'], pos['r'], pos['sigma'], pos['option_type']
            )

            multiplier = pos['quantity'] * pos.get('lot_size', 1)

            for greek_name, greek_value in greeks.items():
                portfolio[greek_name] += greek_value * multiplier

        return portfolio

    def delta_hedge_quantity(self, option_delta: float, option_quantity: int,
                            lot_size: int = 1) -> int:
        """
        Calculate number of underlying shares needed to delta hedge

        Returns:
        --------
        int : Number of underlying shares (negative means short)
        """
        total_delta = option_delta * option_quantity * lot_size
        return -int(round(total_delta))

    def gamma_risk(self, gamma: float, spot_move: float, quantity: int = 1,
                  lot_size: int = 1) -> float:
        """
        Calculate potential delta change due to spot move (gamma risk)

        Parameters:
        -----------
        gamma : float
            Current gamma
        spot_move : float
            Expected spot price move (absolute value)

        Returns:
        --------
        float : Change in delta
        """
        return 0.5 * gamma * (spot_move ** 2) * quantity * lot_size


# Vectorized Greeks for options chain
class GreeksVectorized(Greeks):
    """Vectorized Greeks calculation for options chains"""

    def delta_vectorized(self, S: Union[float, np.ndarray],
                        K: Union[float, np.ndarray],
                        T: Union[float, np.ndarray],
                        r: Union[float, np.ndarray],
                        sigma: Union[float, np.ndarray],
                        option_type: Union[str, np.ndarray] = 'call') -> np.ndarray:
        """Vectorized delta calculation"""
        S, K, T, r, sigma = map(np.asarray, [S, K, T, r, sigma])

        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))

        if isinstance(option_type, str):
            if option_type.lower() == 'call':
                return norm.cdf(d1)
            else:
                return norm.cdf(d1) - 1
        else:
            # Handle array of option types
            delta = np.where(option_type == 'call', norm.cdf(d1), norm.cdf(d1) - 1)
            return delta

    def gamma_vectorized(self, S: Union[float, np.ndarray],
                        K: Union[float, np.ndarray],
                        T: Union[float, np.ndarray],
                        r: Union[float, np.ndarray],
                        sigma: Union[float, np.ndarray]) -> np.ndarray:
        """Vectorized gamma calculation"""
        S, K, T, r, sigma = map(np.asarray, [S, K, T, r, sigma])

        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
        return gamma


if __name__ == "__main__":
    # Example: Nifty ATM option Greeks
    greeks_calc = Greeks()

    S = 19500  # Nifty spot
    K = 19500  # ATM strike
    T = 7 / 365  # 7 days to expiry
    r = 0.07  # 7% risk-free rate
    sigma = 0.15  # 15% volatility

    print("=" * 60)
    print("NIFTY 19500 CE - Greeks Analysis")
    print("=" * 60)

    greeks = greeks_calc.all_greeks(S, K, T, r, sigma, 'call')

    for greek_name, greek_value in greeks.items():
        print(f"{greek_name.capitalize():12s}: {greek_value:12.6f}")

    print("\n" + "=" * 60)
    print("Portfolio Greeks Example")
    print("=" * 60)

    # Example portfolio: Long 2 lots of 19500 CE, Short 1 lot of 19600 CE
    positions = [
        {'S': 19500, 'K': 19500, 'T': 7/365, 'r': 0.07, 'sigma': 0.15,
         'option_type': 'call', 'quantity': 2, 'lot_size': 50},
        {'S': 19500, 'K': 19600, 'T': 7/365, 'r': 0.07, 'sigma': 0.16,
         'option_type': 'call', 'quantity': -1, 'lot_size': 50}
    ]

    portfolio_greeks = greeks_calc.portfolio_greeks(positions)

    for greek_name, greek_value in portfolio_greeks.items():
        print(f"{greek_name.capitalize():12s}: {greek_value:12.2f}")

    # Delta hedging requirement
    hedge_qty = greeks_calc.delta_hedge_quantity(
        portfolio_greeks['delta'] / 100,  # Normalize
        1,
        1
    )
    print(f"\nDelta Hedge Requirement: {hedge_qty} Nifty shares")
