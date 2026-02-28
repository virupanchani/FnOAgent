"""
Risk management for F&O trading
Handles position sizing, margin tracking, and risk limits
"""
import sqlite3
from datetime import datetime
from typing import Dict, Optional
from config.settings import CAPITAL, RISK_PER_TRADE, MAX_POSITIONS, DB_PATH


class FnORiskManager:
    """Risk manager for F&O positions."""
    
    def __init__(self, capital: float = CAPITAL, max_positions: int = MAX_POSITIONS):
        """
        Initialize risk manager.
        
        Args:
            capital: Total trading capital
            max_positions: Maximum open positions
        """
        self.capital = capital
        self.max_positions = max_positions
        self.risk_per_trade = RISK_PER_TRADE
        self.db_path = DB_PATH
        self._init_db()
    
    def _init_db(self):
        """Initialize database for tracking trades."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fno_trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                option_type TEXT NOT NULL,
                strike REAL NOT NULL,
                entry_premium REAL NOT NULL,
                exit_premium REAL,
                lot_size INTEGER NOT NULL,
                entry_time TEXT NOT NULL,
                exit_time TEXT,
                pnl REAL,
                status TEXT NOT NULL,
                exit_reason TEXT,
                strategy TEXT,
                expiry TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def approve_trade(self, symbol: str, option_type: str, strike: float,
                     premium: float, lot_size: int) -> Dict:
        """
        Check if trade is approved based on risk rules.
        
        Args:
            symbol: "NIFTY" or "BANKNIFTY"
            option_type: "CE" or "PE"
            strike: Strike price
            premium: Option premium
            lot_size: Lot size
        
        Returns:
            Dict with approval status and trade parameters
        """
        # Check max positions
        open_positions = self.get_open_positions_count()
        if open_positions >= self.max_positions:
            return {
                "approved": False,
                "reason": f"Max positions ({self.max_positions}) reached"
            }
        
        # Calculate margin requirement (approximate)
        margin = self._calculate_margin(symbol, strike, premium, lot_size)
        
        # Check if we have enough capital
        available_capital = self._get_available_capital()
        if margin > available_capital:
            return {
                "approved": False,
                "reason": f"Insufficient capital (need ₹{margin:,.0f}, have ₹{available_capital:,.0f})"
            }
        
        # Calculate stop loss and target
        stop_loss = premium * 2.0  # 2x premium
        target = premium * 0.5  # 50% profit
        
        return {
            "approved": True,
            "symbol": symbol,
            "option_type": option_type,
            "strike": strike,
            "premium": premium,
            "lot_size": lot_size,
            "margin": margin,
            "stop_loss": stop_loss,
            "target": target
        }
    
    def _calculate_margin(self, symbol: str, strike: float, premium: float,
                         lot_size: int) -> float:
        """
        Calculate approximate margin requirement for option selling.
        
        Uses SPAN + Exposure margin formula (approximate)
        """
        # Simplified margin calculation
        # Actual margin varies based on volatility and other factors
        
        if symbol == "NIFTY":
            # Approximate: 10-15% of contract value
            contract_value = strike * lot_size
            margin = contract_value * 0.12
        else:  # BANKNIFTY
            # Approximate: 10-15% of contract value
            contract_value = strike * lot_size
            margin = contract_value * 0.12
        
        return round(margin, 2)
    
    def _get_available_capital(self) -> float:
        """Calculate available capital after accounting for open positions."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get total margin used by open positions
        cursor.execute("""
            SELECT SUM(entry_premium * lot_size * 0.12) as used_margin
            FROM fno_trades
            WHERE status = 'OPEN'
        """)
        
        result = cursor.fetchone()
        conn.close()
        
        used_margin = result[0] if result[0] else 0
        return self.capital - used_margin
    
    def get_open_positions_count(self) -> int:
        """Get count of open positions."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM fno_trades WHERE status = 'OPEN'")
        count = cursor.fetchone()[0]
        
        conn.close()
        return count
    
    def get_open_positions(self) -> list:
        """Get all open positions."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, symbol, option_type, strike, entry_premium, lot_size,
                   entry_time, strategy, expiry
            FROM fno_trades
            WHERE status = 'OPEN'
        """)
        
        positions = []
        for row in cursor.fetchall():
            positions.append({
                "id": row[0],
                "symbol": row[1],
                "option_type": row[2],
                "strike": row[3],
                "entry_premium": row[4],
                "lot_size": row[5],
                "entry_time": row[6],
                "strategy": row[7],
                "expiry": row[8],
                "stop_loss": row[4] * 2.0,
                "target": row[4] * 0.5
            })
        
        conn.close()
        return positions
    
    def record_trade(self, trade_params: Dict):
        """Record a new trade in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO fno_trades 
            (symbol, option_type, strike, entry_premium, lot_size, entry_time, 
             status, strategy, expiry)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trade_params["symbol"],
            trade_params["option_type"],
            trade_params["strike"],
            trade_params["premium"],
            trade_params["lot_size"],
            datetime.now().isoformat(),
            "OPEN",
            trade_params.get("strategy", "Weekly Option Selling"),
            trade_params.get("expiry", "")
        ))
        
        conn.commit()
        trade_id = cursor.lastrowid
        conn.close()
        
        return trade_id
    
    def close_trade(self, trade_id: int, exit_premium: float, exit_reason: str):
        """Close a trade and record P&L."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get trade details
        cursor.execute("""
            SELECT entry_premium, lot_size
            FROM fno_trades
            WHERE id = ?
        """, (trade_id,))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return
        
        entry_premium, lot_size = row
        
        # Calculate P&L (for option selling)
        pnl = (entry_premium - exit_premium) * lot_size
        
        # Update trade
        cursor.execute("""
            UPDATE fno_trades
            SET exit_premium = ?, exit_time = ?, pnl = ?, 
                status = 'CLOSED', exit_reason = ?
            WHERE id = ?
        """, (exit_premium, datetime.now().isoformat(), pnl, exit_reason, trade_id))
        
        conn.commit()
        conn.close()
        
        return pnl
    
    def get_performance_summary(self) -> Dict:
        """Get overall performance statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winners,
                SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losers,
                SUM(pnl) as total_pnl,
                AVG(pnl) as avg_pnl
            FROM fno_trades
            WHERE status = 'CLOSED'
        """)
        
        row = cursor.fetchone()
        conn.close()
        
        total_trades = row[0] if row[0] else 0
        winners = row[1] if row[1] else 0
        losers = row[2] if row[2] else 0
        total_pnl = row[3] if row[3] else 0
        avg_pnl = row[4] if row[4] else 0
        
        win_rate = (winners / total_trades * 100) if total_trades > 0 else 0
        
        return {
            "total_trades": total_trades,
            "winners": winners,
            "losers": losers,
            "total_pnl": round(total_pnl, 2),
            "avg_pnl": round(avg_pnl, 2),
            "win_rate": round(win_rate, 1)
        }
