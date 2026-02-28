# F&O Agent Setup Guide

## 🚀 Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/virupanchani/FnOAgent.git
cd FnOAgent
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Telegram (Reuse TradeAgent Config)

```bash
# Copy your existing TradeAgent .env file
cp ../TradeAgent/.env .env

# Or create new .env
cp .env.example .env
nano .env
```

**Add Telegram credentials:**
```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Leave Kite fields empty for paper trading
KITE_API_KEY=
KITE_ACCESS_TOKEN=
```

### 4. Test Locally

```bash
# Single scan test
python run_agent.py --once --paper

# View performance
python performance_tracker.py
```

---

## 📊 GitHub Actions Setup

### Add GitHub Secrets

Go to: `https://github.com/virupanchani/FnOAgent/settings/secrets/actions`

Click **"New repository secret"** and add:

| Secret Name | Value |
|------------|-------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token |
| `TELEGRAM_CHAT_ID` | Your Telegram chat ID |

### Workflows

**1. Daily Scan** (Monday 9:45 AM IST)
- Scans for option selling opportunities
- Executes paper trades
- Sends Telegram notifications
- Commits database updates

**2. Weekly Report** (Friday 4:00 PM IST)
- Generates performance summary
- Sends detailed P&L via Telegram

### Manual Trigger

Go to: `https://github.com/virupanchani/FnOAgent/actions`

Click workflow → **"Run workflow"** → **"Run workflow"**

---

## 📱 Telegram Notifications

All messages are prefixed with **"🔷 F&O Agent"** to distinguish from Equity Agent.

**Entry Signal:**
```
🔷 F&O Agent

🎯 F&O ENTRY SIGNAL

📈 SELL NIFTY 22000 PE
💰 Premium: ₹85.00
📦 Lot Size: 50
💵 Margin: ₹45,000
🛑 Stop Loss: ₹170.00
🎯 Target: ₹42.50
⏰ Expiry: 2026-03-05
```

**Performance Report:**
```
🔷 F&O Agent

📊 F&O PERFORMANCE REPORT

Overall Performance:
Total Trades: 48
Win Rate: 100.0%
Total P&L: ₹+129,828
Avg P&L: ₹+2,705
Max Win: ₹2,856
Max Loss: ₹2,059
Open Positions: 0

Last 5 Trades:
✅ NIFTY 22000 PE: ₹+2,798 (Put Target Hit)
✅ NIFTY 21950 PE: ₹+2,795 (Put Target Hit)
...
```

---

## 📈 Performance Tracking

### View Performance

```bash
# Console output + Telegram report
python performance_tracker.py
```

### Database Location

`fno_trades.db` - SQLite database with all trades

### Query Database

```bash
sqlite3 fno_trades.db

# View all trades
SELECT * FROM fno_trades ORDER BY entry_time DESC LIMIT 10;

# View performance
SELECT 
  COUNT(*) as trades,
  SUM(pnl) as total_pnl,
  AVG(pnl) as avg_pnl
FROM fno_trades 
WHERE status = 'CLOSED';
```

---

## 🎯 Strategy Parameters

**Validated via Backtest:**
- Entry: Monday 9:30 AM+
- OTM: 10% (not 15%)
- Exit: Thursday or 50% profit
- Stop Loss: 2x premium
- Lot Size: 1 lot (conservative)

**Backtest Results (1 Year):**
- Total Trades: 48
- Win Rate: 100% (simulated)
- Total Return: +129.83%
- Realistic Expectation: 70-80% win rate

---

## ⚠️ Important Notes

1. **Paper Trading Only** - No real money until validated
2. **No Kite API Required** - Uses Yahoo Finance + Black-Scholes
3. **Simulated Premiums** - Real prices may differ by 5-10%
4. **Conservative Setup** - 1 lot per trade, max 2 positions
5. **Telegram Required** - For notifications and tracking

---

## 🔄 Workflow Schedule

| Workflow | Schedule | Purpose |
|----------|----------|---------|
| Daily Scan | Mon 9:45 AM IST | Find new trades |
| Weekly Report | Fri 4:00 PM IST | Performance summary |

---

## 📞 Support

- **Repository**: https://github.com/virupanchani/FnOAgent
- **Issues**: https://github.com/virupanchani/FnOAgent/issues
- **Equity Agent**: https://github.com/viralpanchani/TradeAgent

---

## 🎯 Next Steps

1. ✅ Add GitHub secrets
2. ✅ Test manual workflow run
3. ✅ Verify Telegram notifications
4. ✅ Monitor for 2-3 weeks
5. ⏳ Consider live trading after validation
