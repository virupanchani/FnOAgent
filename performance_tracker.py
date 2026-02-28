"""
Performance Tracker for F&O Trading Agent
Provides detailed P&L tracking and reporting
"""
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List
from config.settings import DB_PATH
from utils.telegram import send_telegram_message


class PerformanceTracker:
    """Track and report F&O trading performance."""
    
    def __init__(self, db_path: str = DB_PATH):
        """Initialize performance tracker."""
        self.db_path = db_path
    
    def get_overall_pnl(self) -> Dict:
        """Get overall P&L summary."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Overall stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total_trades,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as winners,
                SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losers,
                SUM(pnl) as total_pnl,
                AVG(pnl) as avg_pnl,
                MAX(pnl) as max_win,
                MIN(pnl) as min_loss
            FROM fno_trades
            WHERE status = 'CLOSED'
        """)
        
        row = cursor.fetchone()
        
        total_trades = row[0] if row[0] else 0
        winners = row[1] if row[1] else 0
        losers = row[2] if row[2] else 0
        total_pnl = row[3] if row[3] else 0
        avg_pnl = row[4] if row[4] else 0
        max_win = row[5] if row[5] else 0
        min_loss = row[6] if row[6] else 0
        
        win_rate = (winners / total_trades * 100) if total_trades > 0 else 0
        
        # Open positions
        cursor.execute("SELECT COUNT(*) FROM fno_trades WHERE status = 'OPEN'")
        open_positions = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_trades": total_trades,
            "winners": winners,
            "losers": losers,
            "win_rate": round(win_rate, 1),
            "total_pnl": round(total_pnl, 2),
            "avg_pnl": round(avg_pnl, 2),
            "max_win": round(max_win, 2),
            "max_loss": round(min_loss, 2),
            "open_positions": open_positions
        }
    
    def get_recent_trades(self, limit: int = 10) -> List[Dict]:
        """Get recent trades with details."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                entry_time, exit_time, symbol, option_type, strike,
                entry_premium, exit_premium, lot_size, pnl, exit_reason, status
            FROM fno_trades
            ORDER BY entry_time DESC
            LIMIT ?
        """, (limit,))
        
        trades = []
        for row in cursor.fetchall():
            trades.append({
                "entry_time": row[0],
                "exit_time": row[1],
                "symbol": row[2],
                "option_type": row[3],
                "strike": row[4],
                "entry_premium": row[5],
                "exit_premium": row[6],
                "lot_size": row[7],
                "pnl": row[8],
                "exit_reason": row[9],
                "status": row[10]
            })
        
        conn.close()
        return trades
    
    def get_daily_pnl(self, days: int = 30) -> pd.DataFrame:
        """Get daily P&L for the last N days."""
        conn = sqlite3.connect(self.db_path)
        
        query = """
            SELECT 
                DATE(exit_time) as date,
                COUNT(*) as trades,
                SUM(pnl) as daily_pnl,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losses
            FROM fno_trades
            WHERE status = 'CLOSED' 
                AND exit_time >= date('now', '-{} days')
            GROUP BY DATE(exit_time)
            ORDER BY date DESC
        """.format(days)
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        return df
    
    def get_symbol_breakdown(self) -> pd.DataFrame:
        """Get P&L breakdown by symbol."""
        conn = sqlite3.connect(self.db_path)
        
        query = """
            SELECT 
                symbol,
                COUNT(*) as trades,
                SUM(pnl) as total_pnl,
                AVG(pnl) as avg_pnl,
                SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losses
            FROM fno_trades
            WHERE status = 'CLOSED'
            GROUP BY symbol
            ORDER BY total_pnl DESC
        """
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        
        if not df.empty:
            df['win_rate'] = (df['wins'] / df['trades'] * 100).round(1)
        
        return df
    
    def generate_performance_report(self) -> str:
        """Generate detailed performance report."""
        overall = self.get_overall_pnl()
        recent = self.get_recent_trades(5)
        daily = self.get_daily_pnl(7)
        symbols = self.get_symbol_breakdown()
        
        report = []
        report.append("📊 *F&O PERFORMANCE REPORT*\n")
        
        # Overall stats
        report.append("*Overall Performance:*")
        report.append(f"Total Trades: {overall['total_trades']}")
        report.append(f"Win Rate: {overall['win_rate']}%")
        report.append(f"Total P&L: ₹{overall['total_pnl']:+,.0f}")
        report.append(f"Avg P&L: ₹{overall['avg_pnl']:+,.0f}")
        report.append(f"Max Win: ₹{overall['max_win']:,.0f}")
        report.append(f"Max Loss: ₹{overall['max_loss']:,.0f}")
        report.append(f"Open Positions: {overall['open_positions']}\n")
        
        # Recent trades
        if recent:
            report.append("*Last 5 Trades:*")
            for trade in recent[:5]:
                status_emoji = "✅" if trade['pnl'] and trade['pnl'] > 0 else "❌" if trade['pnl'] and trade['pnl'] < 0 else "🔄"
                if trade['status'] == 'CLOSED':
                    report.append(
                        f"{status_emoji} {trade['symbol']} {trade['strike']} {trade['option_type']}: "
                        f"₹{trade['pnl']:+,.0f} ({trade['exit_reason']})"
                    )
                else:
                    report.append(
                        f"🔄 {trade['symbol']} {trade['strike']} {trade['option_type']}: "
                        f"OPEN @ ₹{trade['entry_premium']:.0f}"
                    )
            report.append("")
        
        # Daily P&L (last 7 days)
        if not daily.empty:
            report.append("*Last 7 Days P&L:*")
            for _, row in daily.iterrows():
                report.append(
                    f"{row['date']}: ₹{row['daily_pnl']:+,.0f} "
                    f"({row['wins']}W/{row['losses']}L)"
                )
            report.append("")
        
        # Symbol breakdown
        if not symbols.empty:
            report.append("*By Symbol:*")
            for _, row in symbols.iterrows():
                report.append(
                    f"{row['symbol']}: ₹{row['total_pnl']:+,.0f} "
                    f"({row['win_rate']:.0f}% WR, {row['trades']} trades)"
                )
        
        return "\n".join(report)
    
    def send_performance_update(self):
        """Send performance update via Telegram."""
        report = self.generate_performance_report()
        send_telegram_message(report)
    
    def print_performance_summary(self):
        """Print performance summary to console."""
        overall = self.get_overall_pnl()
        
        print("\n" + "=" * 60)
        print("  F&O PERFORMANCE SUMMARY")
        print("=" * 60)
        print(f"  Total Trades:     {overall['total_trades']}")
        print(f"  Winners:          {overall['winners']}")
        print(f"  Losers:           {overall['losers']}")
        print(f"  Win Rate:         {overall['win_rate']}%")
        print(f"  Total P&L:        ₹{overall['total_pnl']:+,.0f}")
        print(f"  Avg P&L:          ₹{overall['avg_pnl']:+,.0f}")
        print(f"  Max Win:          ₹{overall['max_win']:,.0f}")
        print(f"  Max Loss:         ₹{overall['max_loss']:,.0f}")
        print(f"  Open Positions:   {overall['open_positions']}")
        print("=" * 60 + "\n")


def main():
    """Generate and display performance report."""
    tracker = PerformanceTracker()
    
    # Print to console
    tracker.print_performance_summary()
    
    # Show recent trades
    print("Recent Trades:")
    recent = tracker.get_recent_trades(10)
    for trade in recent:
        status = "OPEN" if trade['status'] == 'OPEN' else f"₹{trade['pnl']:+,.0f}"
        print(f"  {trade['entry_time'][:10]} | {trade['symbol']} {trade['strike']} {trade['option_type']} | {status}")
    
    # Send to Telegram
    print("\nSending performance report to Telegram...")
    tracker.send_performance_update()


if __name__ == "__main__":
    main()
