"""
Base strategy class for F&O trading
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import pandas as pd


class BaseStrategy(ABC):
    """Abstract base class for F&O trading strategies."""
    
    def __init__(self, name: str):
        """
        Initialize strategy.
        
        Args:
            name: Strategy name
        """
        self.name = name
    
    @abstractmethod
    def generate_signals(self, option_chain: Dict, spot_price: float,
                        symbol: str, expiry: str) -> List[Dict]:
        """
        Generate trading signals from option chain.
        
        Args:
            option_chain: Option chain data
            spot_price: Current spot price
            symbol: "NIFTY" or "BANKNIFTY"
            expiry: Expiry date
        
        Returns:
            List of signal dictionaries with trade details
        """
        pass
    
    @abstractmethod
    def should_exit(self, position: Dict, current_premium: float) -> tuple:
        """
        Check if position should be exited.
        
        Args:
            position: Position details
            current_premium: Current option premium
        
        Returns:
            (should_exit: bool, reason: str)
        """
        pass
    
    def calculate_position_pnl(self, entry_premium: float, current_premium: float,
                              lot_size: int, position_type: str = "SELL") -> float:
        """
        Calculate P&L for option position.
        
        Args:
            entry_premium: Premium at entry
            current_premium: Current premium
            lot_size: Number of lots
            position_type: "SELL" or "BUY"
        
        Returns:
            P&L in rupees
        """
        if position_type == "SELL":
            # Profit when premium decreases
            pnl = (entry_premium - current_premium) * lot_size
        else:  # BUY
            # Profit when premium increases
            pnl = (current_premium - entry_premium) * lot_size
        
        return pnl
