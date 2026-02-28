"""
Paper trading execution for F&O options
Simulates option trades without real money
"""
from typing import Dict
from datetime import datetime
from risk.fno_risk_manager import FnORiskManager
from utils.telegram import send_entry_signal, send_exit_signal


class PaperTrader:
    """Paper trading executor for F&O options."""
    
    def __init__(self):
        """Initialize paper trader."""
        self.risk_mgr = FnORiskManager()
    
    def execute_trade(self, signal: Dict) -> bool:
        """
        Execute a paper trade.
        
        Args:
            signal: Trade signal with all parameters
        
        Returns:
            True if trade executed successfully
        """
        # Get lot size from signal or use default
        lot_size = signal.get("lot_size", self._get_lot_size(signal["symbol"]))
        
        # Check risk approval
        approval = self.risk_mgr.approve_trade(
            symbol=signal["symbol"],
            option_type=signal["option_type"],
            strike=signal["strike"],
            premium=signal["premium"],
            lot_size=lot_size
        )
        
        if not approval["approved"]:
            print(f"  ❌ Trade rejected: {approval['reason']}")
            return False
        
        # Record trade
        trade_params = {
            "symbol": signal["symbol"],
            "option_type": signal["option_type"],
            "strike": signal["strike"],
            "premium": signal["premium"],
            "lot_size": lot_size,
            "strategy": signal.get("strategy", "Weekly Option Selling"),
            "expiry": signal.get("expiry", "")
        }
        
        trade_id = self.risk_mgr.record_trade(trade_params)
        
        # Send Telegram notification
        send_entry_signal(
            symbol=signal["symbol"],
            option_type=signal["option_type"],
            strike=signal["strike"],
            premium=signal["premium"],
            lot_size=lot_size,
            margin=approval["margin"],
            stop_loss=approval["stop_loss"],
            target=approval["target"],
            expiry=signal.get("expiry", "")
        )
        
        print(f"  ✅ SELL {signal['symbol']} {signal['strike']} {signal['option_type']} @ ₹{signal['premium']:.2f}")
        print(f"     Lot Size: {lot_size} | Margin: ₹{approval['margin']:,.0f}")
        print(f"     SL: ₹{approval['stop_loss']:.2f} | Target: ₹{approval['target']:.2f}")
        
        return True
    
    def monitor_positions(self, option_chain_scanner, strategy) -> list:
        """
        Monitor open positions and check exit conditions.
        
        Args:
            option_chain_scanner: Scanner to get current premiums
            strategy: Strategy instance for exit logic
        
        Returns:
            List of closed positions
        """
        open_positions = self.risk_mgr.get_open_positions()
        closed = []
        
        for position in open_positions:
            # Get current premium
            current_premium = self._get_current_premium(
                option_chain_scanner,
                position["symbol"],
                position["option_type"],
                position["strike"],
                position["expiry"]
            )
            
            if current_premium is None:
                continue
            
            # Check exit conditions
            should_exit, reason = strategy.should_exit(position, current_premium)
            
            if should_exit:
                # Close position
                pnl = self.risk_mgr.close_trade(
                    position["id"],
                    current_premium,
                    reason
                )
                
                # Send exit notification
                send_exit_signal(
                    symbol=position["symbol"],
                    option_type=position["option_type"],
                    strike=position["strike"],
                    entry_premium=position["entry_premium"],
                    exit_premium=current_premium,
                    pnl=pnl,
                    reason=reason
                )
                
                closed.append({
                    "symbol": position["symbol"],
                    "option_type": position["option_type"],
                    "strike": position["strike"],
                    "pnl": pnl,
                    "reason": reason
                })
                
                print(f"  🔔 Closed {position['symbol']} {position['strike']} {position['option_type']}")
                print(f"     Entry: ₹{position['entry_premium']:.2f} | Exit: ₹{current_premium:.2f}")
                print(f"     P&L: ₹{pnl:+,.0f} | Reason: {reason}")
        
        return closed
    
    def _get_current_premium(self, scanner, symbol: str, option_type: str,
                            strike: float, expiry: str) -> float:
        """Get current premium for an option."""
        try:
            option_chain = scanner.get_option_chain(symbol, expiry)
            if strike in option_chain[option_type]:
                return option_chain[option_type][strike]["ltp"]
        except Exception as e:
            print(f"  Error fetching premium: {e}")
        
        return None
    
    def _get_lot_size(self, symbol: str) -> int:
        """Get standard lot size for symbol."""
        if symbol == "NIFTY":
            return 50
        else:  # BANKNIFTY
            return 15
    
    def get_performance(self) -> Dict:
        """Get performance summary."""
        return self.risk_mgr.get_performance_summary()
