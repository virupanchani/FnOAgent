"""
Configuration settings for F&O Trading Agent
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Kite Connect API
KITE_API_KEY = os.getenv("KITE_API_KEY", "")
KITE_ACCESS_TOKEN = os.getenv("KITE_ACCESS_TOKEN", "")

# Telegram Bot
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Trading Configuration
CAPITAL = float(os.getenv("CAPITAL", "100000"))
RISK_PER_TRADE = float(os.getenv("RISK_PER_TRADE", "0.02"))
MAX_POSITIONS = int(os.getenv("MAX_POSITIONS", "2"))

# Strategy Parameters
STRATEGY = "weekly_option_selling"
INSTRUMENTS = ["NIFTY", "BANKNIFTY"]

# Option Selling Parameters
OTM_PERCENTAGE = 0.15  # 15% OTM for strike selection
PROFIT_TARGET = 0.50   # Exit at 50% profit
STOP_LOSS_MULTIPLIER = 2.0  # Stop loss at 2x premium
LOT_SIZE = 1  # Conservative: 1 lot per trade

# Timing
ENTRY_DAY = "Monday"
ENTRY_TIME = "09:30"
EXIT_DAYS = ["Thursday", "Friday"]
SCAN_INTERVAL_SECONDS = 300  # 5 minutes

# Database
DB_PATH = "fno_trades.db"
