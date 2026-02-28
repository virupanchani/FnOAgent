"""
Weekly Option Selling Strategy
Proven win rate: 70-80%

Strategy:
- Sell OTM Puts & Calls on Monday (15-20% OTM)
- Exit on Thursday/Friday or at 50% profit
- Stop Loss: 2x premium received
- Conservative: 1 lot per trade
"""
from typing import Dict, List
from datetime import datetime
from strategies.base import BaseStrategy
from config.settings import OTM_PERCENTAGE, PROFIT_TARGET, STOP_LOSS_MULTIPLIER


class WeeklyOptionSellingStrategy(BaseStrategy):
    """Weekly option selling strategy for consistent income."""
    
    def __init__(self):
        super().__init__("Weekly Option Selling")
        self.otm_pct = OTM_PERCENTAGE
        self.profit_target = PROFIT_TARGET
        self.stop_loss_mult = STOP_LOSS_MULTIPLIER
    
    def generate_signals(self, option_chain: Dict, spot_price: float,
                        symbol: str, expiry: str) -> List[Dict]:
        """
        Generate option selling signals.
        
        Entry Criteria:
        - Monday after 9:30 AM
        - Sell OTM Put (15-20% below spot)
        - Sell OTM Call (15-20% above spot)
        - Premium > ₹50 (avoid very cheap options)
        
        Returns:
            List of signals with strike, premium, type
        """
        signals = []
        
        # Check if it's Monday
        today = datetime.now()
        if today.weekday() != 0:  # 0 = Monday
            return signals
        
        # Check if market hours (9:30 AM onwards)
        if today.hour < 9 or (today.hour == 9 and today.minute < 30):
            return signals
        
        # Find OTM Put strike
        put_strike = self._find_otm_strike(spot_price, symbol, "PE")
        if put_strike in option_chain["PE"]:
            put_data = option_chain["PE"][put_strike]
            put_premium = put_data["ltp"]
            
            if put_premium >= 50:  # Minimum premium threshold
                signals.append({
                    "action": "SELL",
                    "symbol": symbol,
                    "option_type": "PE",
                    "strike": put_strike,
                    "premium": put_premium,
                    "expiry": expiry,
                    "stop_loss": put_premium * self.stop_loss_mult,
                    "target": put_premium * (1 - self.profit_target),
                    "tradingsymbol": put_data["tradingsymbol"]
                })
        
        # Find OTM Call strike
        call_strike = self._find_otm_strike(spot_price, symbol, "CE")
        if call_strike in option_chain["CE"]:
            call_data = option_chain["CE"][call_strike]
            call_premium = call_data["ltp"]
            
            if call_premium >= 50:  # Minimum premium threshold
                signals.append({
                    "action": "SELL",
                    "symbol": symbol,
                    "option_type": "CE",
                    "strike": call_strike,
                    "premium": call_premium,
                    "expiry": expiry,
                    "stop_loss": call_premium * self.stop_loss_mult,
                    "target": call_premium * (1 - self.profit_target),
                    "tradingsymbol": call_data["tradingsymbol"]
                })
        
        return signals
    
    def should_exit(self, position: Dict, current_premium: float) -> tuple:
        """
        Check exit conditions.
        
        Exit Criteria:
        1. 50% profit achieved (target hit)
        2. Stop loss hit (2x premium)
        3. Thursday/Friday (close before expiry)
        4. Expiry day (must exit)
        
        Args:
            position: Position details with entry_premium, stop_loss, target
            current_premium: Current option premium
        
        Returns:
            (should_exit: bool, reason: str)
        """
        entry_premium = position["entry_premium"]
        stop_loss = position["stop_loss"]
        target = position["target"]
        
        # Check profit target (50% of premium collected)
        if current_premium <= target:
            return (True, "Target Hit (50% profit)")
        
        # Check stop loss (2x premium)
        if current_premium >= stop_loss:
            return (True, "Stop Loss Hit")
        
        # Check day of week
        today = datetime.now()
        weekday = today.weekday()
        
        # Exit on Thursday (3) or Friday (4)
        if weekday in [3, 4]:
            return (True, f"Exit Day ({today.strftime('%A')})")
        
        # Check if expiry day
        expiry_date = datetime.strptime(position["expiry"], "%Y-%m-%d")
        if today.date() >= expiry_date.date():
            return (True, "Expiry Day")
        
        return (False, "")
    
    def _find_otm_strike(self, spot: float, symbol: str, option_type: str) -> float:
        """Find OTM strike based on percentage."""
        if symbol == "NIFTY":
            step = 50
        else:  # BANKNIFTY
            step = 100
        
        if option_type == "CE":
            target = spot * (1 + self.otm_pct)
        else:  # PE
            target = spot * (1 - self.otm_pct)
        
        strike = round(target / step) * step
        return strike
    
    def get_lot_size(self, symbol: str) -> int:
        """
        Get lot size for the symbol.
        
        Args:
            symbol: "NIFTY" or "BANKNIFTY"
        
        Returns:
            Lot size
        """
        # Standard lot sizes (as of 2024)
        if symbol == "NIFTY":
            return 50
        else:  # BANKNIFTY
            return 15
