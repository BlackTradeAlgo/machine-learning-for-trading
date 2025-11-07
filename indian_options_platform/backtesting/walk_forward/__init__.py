"""
Walk-Forward Optimization
Out-of-sample testing to prevent overfitting
"""

from .walk_forward_optimizer import (
    WalkForwardOptimizer,
    WalkForwardResults,
    WalkForwardWindow
)

__all__ = [
    'WalkForwardOptimizer',
    'WalkForwardResults',
    'WalkForwardWindow'
]
