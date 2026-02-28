"""
Telegram notification utilities for F&O Trading Agent
Reuses TradeAgent Telegram configuration
"""
import os
import requests
from config.settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

AGENT_NAME = "F&O Agent"


def send_telegram_message(message: str) -> bool:
    """Send a message to Telegram with F&O agent prefix."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("  [Telegram not configured]")
        return False
    
    # Add agent name prefix to distinguish from equity agent
    prefixed_message = f"🔷 *{AGENT_NAME}*\n\n{message}"
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": prefixed_message,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("  [Telegram] Message sent")
            return True
        else:
            print(f"  [Telegram] Error: {response.status_code}")
            return False
    except Exception as e:
        print(f"  [Telegram] Failed: {e}")
        return False


def send_entry_signal(symbol: str, option_type: str, strike: float, premium: float,
                     lot_size: int, margin: float, stop_loss: float, target: float,
                     expiry: str):
    """Send option entry signal to Telegram."""
    msg = (
        f"🎯 *F&O ENTRY SIGNAL*\n\n"
        f"📈 *SELL {symbol} {strike} {option_type}*\n"
        f"💰 Premium: ₹{premium:.2f}\n"
        f"📦 Lot Size: {lot_size}\n"
        f"💵 Margin: ₹{margin:,.0f}\n"
        f"🛑 Stop Loss: ₹{stop_loss:.2f} (2x premium)\n"
        f"🎯 Target: ₹{target:.2f} (50% profit)\n"
        f"⏰ Expiry: {expiry}\n\n"
        f"⚡ Strategy: Weekly Option Selling"
    )
    return send_telegram_message(msg)


def send_exit_signal(symbol: str, option_type: str, strike: float, entry_premium: float,
                    exit_premium: float, pnl: float, reason: str):
    """Send option exit signal to Telegram."""
    emoji = "✅" if pnl > 0 else "❌"
    msg = (
        f"{emoji} *F&O EXIT SIGNAL*\n\n"
        f"📉 *{symbol} {strike} {option_type}*\n"
        f"💰 Entry Premium: ₹{entry_premium:.2f}\n"
        f"🏁 Exit Premium: ₹{exit_premium:.2f}\n"
        f"💸 P&L: ₹{pnl:+,.0f}\n"
        f"📌 Reason: {reason}"
    )
    return send_telegram_message(msg)


def send_daily_summary(open_positions: int, total_pnl: float, win_rate: float,
                      today_trades: int):
    """Send daily F&O summary to Telegram."""
    msg = (
        f"📊 *F&O DAILY SUMMARY*\n\n"
        f"📂 Open Positions: {open_positions}\n"
        f"💰 Total P&L: ₹{total_pnl:+,.0f}\n"
        f"🎯 Win Rate: {win_rate:.1f}%\n"
        f"📈 Today's Trades: {today_trades}\n\n"
        f"⚡ Strategy: Weekly Option Selling"
    )
    return send_telegram_message(msg)


def send_risk_alert(message: str):
    """Send risk management alert to Telegram."""
    msg = f"⚠️ *RISK ALERT*\n\n{message}"
    return send_telegram_message(msg)
