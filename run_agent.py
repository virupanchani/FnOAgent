"""
F&O Trading Agent - Main Runner
Weekly Option Selling Strategy for Nifty & Bank Nifty

Usage:
    python run_agent.py --paper    # Paper trading mode
    python run_agent.py --live     # Live trading mode (requires confirmation)
    python run_agent.py --once     # Single scan cycle
"""
import sys
import time
import argparse
from datetime import datetime

from scanner.option_chain import OptionChainScanner
from strategies.weekly_option_selling import WeeklyOptionSellingStrategy
from execution.paper_trader import PaperTrader
from utils.telegram import send_telegram_message, send_daily_summary
from config.settings import INSTRUMENTS, SCAN_INTERVAL_SECONDS


def print_header():
    """Print agent header."""
    print("\n" + "=" * 60)
    print("  F&O TRADING AGENT")
    print("  Strategy: Weekly Option Selling")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print("  Instruments: Nifty 50, Bank Nifty")
    print("  Capital:     ₹1,00,000")
    print("  Risk/Trade:  2%")
    print("  Max Pos:     2")
    print("  Lot Size:    1 (Conservative)")
    print("=" * 60 + "\n")


def run_scan_cycle(scanner, strategy, trader):
    """Run one complete scan cycle."""
    print(f"\n{'─' * 60}")
    print(f"  SCAN CYCLE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'─' * 60}")
    
    # Monitor existing positions
    open_positions = trader.risk_mgr.get_open_positions()
    if open_positions:
        print(f"\n  Monitoring {len(open_positions)} open positions...")
        closed = trader.monitor_positions(scanner, strategy)
        if closed:
            for c in closed:
                print(f"    ✓ Closed {c['symbol']} {c['strike']} {c['option_type']}: {c['reason']} (P&L: ₹{c['pnl']:+,.0f})")
    
    # Scan for new signals
    print(f"\n  Scanning for new signals...")
    signals_generated = 0
    
    for symbol in INSTRUMENTS:
        try:
            # Get spot price
            spot = scanner.get_spot_price(symbol)
            print(f"\n  {symbol}: Spot = ₹{spot:,.2f}")
            
            # Get weekly expiry
            expiry = scanner.get_weekly_expiry(symbol)
            print(f"  Expiry: {expiry}")
            
            # Get option chain
            option_chain = scanner.get_option_chain(symbol, expiry)
            
            # Generate signals
            signals = strategy.generate_signals(option_chain, spot, symbol, expiry)
            
            if signals:
                print(f"  Found {len(signals)} signal(s)")
                for signal in signals:
                    signal["strategy"] = strategy.name
                    signal["lot_size"] = strategy.get_lot_size(symbol)
                    
                    # Execute trade
                    if trader.execute_trade(signal):
                        signals_generated += 1
            else:
                print(f"  No signals (not Monday or conditions not met)")
        
        except Exception as e:
            print(f"  Error scanning {symbol}: {e}")
            import traceback
            traceback.print_exc()
    
    # Print summary
    perf = trader.get_performance()
    print(f"\n  SUMMARY: Open={len(open_positions)} | Signals={signals_generated}")
    print(f"  Performance: Trades={perf['total_trades']} | P&L=₹{perf['total_pnl']:+,.0f} | WR={perf['win_rate']}%")
    
    return signals_generated


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="F&O Trading Agent")
    parser.add_argument("--paper", action="store_true", help="Paper trading mode")
    parser.add_argument("--live", action="store_true", help="Live trading mode")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    args = parser.parse_args()
    
    # Determine mode
    if args.live:
        mode = "LIVE"
        print("\n⚠️  LIVE TRADING MODE - NOT IMPLEMENTED YET")
        print("Please use --paper for paper trading")
        sys.exit(1)
    else:
        mode = "PAPER"
    
    single_run = args.once
    
    print_header()
    print(f"  Mode: {mode} Trading")
    print(f"  Run Type: {'Single Scan' if single_run else 'Continuous'}\n")
    
    # Initialize components
    scanner = OptionChainScanner()  # No Kite client for paper trading
    strategy = WeeklyOptionSellingStrategy()
    trader = PaperTrader()
    
    # Send startup notification
    try:
        send_telegram_message(
            f"🚀 *F&O Agent Started*\n\n"
            f"Strategy: {strategy.name}\n"
            f"Mode: {mode}\n"
            f"Instruments: {', '.join(INSTRUMENTS)}"
        )
    except Exception:
        print("  [Telegram not configured]")
    
    if single_run:
        # Run once and exit
        run_scan_cycle(scanner, strategy, trader)
        perf = trader.get_performance()
        print(f"\n  Final Performance: {perf}")
        return
    
    # Continuous mode
    print(f"  Starting continuous monitoring (scan every {SCAN_INTERVAL_SECONDS}s)...\n")
    
    while True:
        try:
            run_scan_cycle(scanner, strategy, trader)
            
            print(f"\n  Next scan in {SCAN_INTERVAL_SECONDS}s...")
            time.sleep(SCAN_INTERVAL_SECONDS)
        
        except KeyboardInterrupt:
            print("\n\n  Stopping agent...")
            perf = trader.get_performance()
            print(f"  Final Performance: {perf}")
            
            # Send shutdown notification
            try:
                send_daily_summary(
                    open_positions=len(trader.risk_mgr.get_open_positions()),
                    total_pnl=perf['total_pnl'],
                    win_rate=perf['win_rate'],
                    today_trades=perf['total_trades']
                )
            except Exception:
                pass
            
            sys.exit(0)
        
        except Exception as e:
            print(f"\n  Error in main loop: {e}")
            import traceback
            traceback.print_exc()
            time.sleep(60)


if __name__ == "__main__":
    main()
