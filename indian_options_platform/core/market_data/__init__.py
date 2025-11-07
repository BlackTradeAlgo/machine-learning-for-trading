"""
Market Data Integration Module
Supports NSE, BSE, and multiple broker APIs
"""

from .nse_data import NSEData
try:
    from .bse_data import BSEData
except (ImportError, AttributeError):
    BSEData = None

try:
    from .options_chain import OptionsChainAnalyzer
except (ImportError, AttributeError):
    OptionsChainAnalyzer = None

__all__ = ['NSEData', 'BSEData', 'OptionsChainAnalyzer']
