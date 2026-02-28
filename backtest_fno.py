"""
Backtesting engine for F&O option selling strategy

Note: Historical option data is limited. This uses:
1. Historical spot prices (available via yfinance)
2. Black-Scholes model to estimate option premiums
3. Historical volatility for IV estimation

For production backtesting, use actual option chain data from NSE/broker.
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List
import yfinance as yf

from strategies.weekly_option_selling import WeeklyOptionSellingStrategy
from utils.greeks import calculate_greeks


class FnOBacktester:
    """Backtester for F&O option selling strategies."""
    
    def __init__(self, initial_capital: float = 100000):
        """
        Initialize backtester.
        
        Args:
            initial_capital: Starting capital
        """
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.trades = []
        self.equity_curve = []
    
    def fetch_historical_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """
        Fetch historical spot price data.
        
        Args:
            symbol: "^NSEI" for Nifty or "^NSEBANK" for Bank Nifty
            start_date: Start date "YYYY-MM-DD"
            end_date: End date "YYYY-MM-DD"
        
        Returns:
            DataFrame with OHLCV data
        """
        print(f"  Fetching {symbol} data from {start_date} to {end_date}...")
        
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=start_date, end=end_date, interval="1d")
        
        if df.empty:
            raise ValueError(f"No data found for {symbol}")
        
        # Calculate historical volatility (20-day rolling)
        df['returns'] = df['Close'].pct_change()
        df['volatility'] = df['returns'].rolling(window=20).std() * np.sqrt(252)
        df['volatility'] = df['volatility'].fillna(0.3)  # Default 30% IV
        
        print(f"  Loaded {len(df)} days of data")
        return df
    
    def get_weekly_expiries(self, start_date: str, end_date: str, 
                           expiry_day: int = 3) -> List[str]:
        """
        Get all weekly expiry dates in the period.
        
        Args:
            start_date: Start date
            end_date: End date
            expiry_day: Day of week (3=Thursday for Nifty, 2=Wednesday for BankNifty)
        
        Returns:
            List of expiry dates
        """
        expiries = []
        current = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        
        while current <= end:
            if current.weekday() == expiry_day:
                expiries.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)
        
        return expiries
    
    def estimate_option_premium(self, spot: float, strike: float, 
                               days_to_expiry: int, volatility: float,
                               option_type: str = "PE") -> float:
        """
        Estimate option premium using Black-Scholes.
        
        Args:
            spot: Spot price
            strike: Strike price
            days_to_expiry: Days to expiry
            volatility: Implied volatility
            option_type: "CE" or "PE"
        
        Returns:
            Estimated premium
        """
        time_to_expiry = days_to_expiry / 365.0
        
        if time_to_expiry <= 0:
            # At expiry, intrinsic value only
            if option_type == "CE":
                return max(0, spot - strike)
            else:  # PE
                return max(0, strike - spot)
        
        # Ensure volatility is reasonable
        if volatility <= 0 or np.isnan(volatility):
            volatility = 0.20  # Default 20% IV
        
        try:
            greeks = calculate_greeks(spot, strike, time_to_expiry, volatility, 
                                     risk_free_rate=0.07, option_type=option_type)
            premium = greeks["premium"]
            
            # Sanity check - premium should be positive for OTM options
            if premium <= 0:
                # Fallback: simple time value estimation
                moneyness = abs(spot - strike) / spot
                premium = spot * 0.01 * np.sqrt(time_to_expiry) * (1 + moneyness * 2)
            
            return max(premium, 1)  # Minimum ₹1
        except Exception as e:
            # Fallback calculation
            moneyness = abs(spot - strike) / spot
            premium = spot * 0.01 * np.sqrt(time_to_expiry) * (1 + moneyness * 2)
            return max(premium, 1)
    
    def backtest_weekly_option_selling(self, symbol: str, start_date: str, 
                                      end_date: str, otm_pct: float = 0.15) -> Dict:
        """
        Backtest weekly option selling strategy.
        
        Strategy:
        - Every Monday: Sell OTM Put & Call (15% OTM)
        - Exit on Thursday or when 50% profit or 2x loss
        
        Args:
            symbol: "^NSEI" or "^NSEBANK"
            start_date: Start date
            end_date: End date
            otm_pct: OTM percentage (default 15%)
        
        Returns:
            Backtest results
        """
        # Fetch historical data
        df = self.fetch_historical_data(symbol, start_date, end_date)
        
        # Get weekly expiries
        expiry_day = 3 if symbol == "^NSEI" else 2  # Thursday for Nifty, Wednesday for BankNifty
        expiries = self.get_weekly_expiries(start_date, end_date, expiry_day)
        
        print(f"\n  Backtesting {len(expiries)} weekly cycles...")
        
        symbol_name = "NIFTY" if symbol == "^NSEI" else "BANKNIFTY"
        lot_size = 50 if symbol == "^NSEI" else 15
        
        trades_attempted = 0
        trades_skipped = 0
        
        for expiry_date in expiries:
            trades_attempted += 1
            expiry_dt = datetime.strptime(expiry_date, "%Y-%m-%d")
            
            # Find Monday of the same week (entry day)
            # If expiry is Thursday (weekday 3), Monday is 3 days before
            days_back = expiry_dt.weekday()  # 0=Mon, 3=Thu
            entry_dt = expiry_dt - timedelta(days=days_back)
            
            # Find nearest trading day to Monday
            entry_date = None
            for offset in range(5):  # Check Mon-Fri
                check_date = (entry_dt + timedelta(days=offset)).strftime("%Y-%m-%d")
                if check_date in df.index:
                    entry_date = check_date
                    entry_dt = datetime.strptime(entry_date, "%Y-%m-%d")
                    break
            
            if not entry_date:
                continue
            
            # Entry conditions
            entry_spot = df.loc[entry_date, 'Close']
            entry_vol = df.loc[entry_date, 'volatility']
            
            # Calculate strikes
            put_strike = round(entry_spot * (1 - otm_pct) / 50) * 50
            call_strike = round(entry_spot * (1 + otm_pct) / 50) * 50
            
            # Calculate days to expiry
            days_to_expiry = (expiry_dt - entry_dt).days
            
            # Estimate premiums at entry
            put_premium = self.estimate_option_premium(
                entry_spot, put_strike, days_to_expiry, entry_vol, "PE"
            )
            call_premium = self.estimate_option_premium(
                entry_spot, call_strike, days_to_expiry, entry_vol, "CE"
            )
            
            # Skip if premiums too low (₹20 minimum for realistic trading)
            if put_premium < 20 or call_premium < 20:
                trades_skipped += 1
                if trades_attempted <= 3:  # Debug first few
                    print(f"    Skipped {entry_date}: Put=₹{put_premium:.0f}, Call=₹{call_premium:.0f}")
                continue
            
            if trades_attempted <= 3:  # Debug first few
                print(f"    Trade {trades_attempted}: Entry={entry_date}, Spot=₹{entry_spot:.0f}, Put=₹{put_premium:.0f}, Call=₹{call_premium:.0f}")
            
            # Simulate holding until exit
            exit_date = None
            exit_reason = ""
            put_exit_premium = 0
            call_exit_premium = 0
            
            # Check each day until expiry
            current_dt = entry_dt + timedelta(days=1)
            while current_dt <= expiry_dt:
                current_date = current_dt.strftime("%Y-%m-%d")
                
                if current_date not in df.index:
                    current_dt += timedelta(days=1)
                    continue
                
                current_spot = df.loc[current_date, 'Close']
                current_vol = df.loc[current_date, 'volatility']
                days_left = (expiry_dt - current_dt).days
                
                # Estimate current premiums
                put_current = self.estimate_option_premium(
                    current_spot, put_strike, days_left, current_vol, "PE"
                )
                call_current = self.estimate_option_premium(
                    current_spot, call_strike, days_left, current_vol, "CE"
                )
                
                # Check exit conditions
                # 1. Profit target (50% of premium)
                if put_current <= put_premium * 0.5:
                    exit_date = current_date
                    exit_reason = "Put Target Hit"
                    put_exit_premium = put_current
                    call_exit_premium = call_current
                    break
                
                if call_current <= call_premium * 0.5:
                    exit_date = current_date
                    exit_reason = "Call Target Hit"
                    put_exit_premium = put_current
                    call_exit_premium = call_current
                    break
                
                # 2. Stop loss (2x premium)
                if put_current >= put_premium * 2.0:
                    exit_date = current_date
                    exit_reason = "Put Stop Loss"
                    put_exit_premium = put_current
                    call_exit_premium = call_current
                    break
                
                if call_current >= call_premium * 2.0:
                    exit_date = current_date
                    exit_reason = "Call Stop Loss"
                    put_exit_premium = put_current
                    call_exit_premium = call_current
                    break
                
                # 3. Exit on Thursday (day before expiry for safety)
                if current_dt.weekday() == 3:  # Thursday
                    exit_date = current_date
                    exit_reason = "Thursday Exit"
                    put_exit_premium = put_current
                    call_exit_premium = call_current
                    break
                
                current_dt += timedelta(days=1)
            
            # If no exit, close at expiry
            if not exit_date:
                exit_date = expiry_date
                exit_reason = "Expiry"
                exit_spot = df.loc[expiry_date, 'Close'] if expiry_date in df.index else entry_spot
                put_exit_premium = max(0, put_strike - exit_spot)
                call_exit_premium = max(0, exit_spot - call_strike)
            
            # Calculate P&L
            put_pnl = (put_premium - put_exit_premium) * lot_size
            call_pnl = (call_premium - call_exit_premium) * lot_size
            total_pnl = put_pnl + call_pnl
            
            # Record trades
            self.trades.append({
                "entry_date": entry_date,
                "exit_date": exit_date,
                "symbol": symbol_name,
                "put_strike": put_strike,
                "call_strike": call_strike,
                "put_entry_premium": put_premium,
                "call_entry_premium": call_premium,
                "put_exit_premium": put_exit_premium,
                "call_exit_premium": call_exit_premium,
                "put_pnl": put_pnl,
                "call_pnl": call_pnl,
                "total_pnl": total_pnl,
                "exit_reason": exit_reason
            })
            
            # Update capital
            self.capital += total_pnl
            self.equity_curve.append({
                "date": exit_date,
                "capital": self.capital,
                "pnl": total_pnl
            })
        
        return self.generate_report()
    
    def generate_report(self) -> Dict:
        """Generate backtest performance report."""
        if not self.trades:
            return {"error": "No trades executed"}
        
        df_trades = pd.DataFrame(self.trades)
        
        # Calculate metrics
        total_trades = len(df_trades)
        winners = len(df_trades[df_trades['total_pnl'] > 0])
        losers = len(df_trades[df_trades['total_pnl'] < 0])
        win_rate = (winners / total_trades * 100) if total_trades > 0 else 0
        
        total_pnl = df_trades['total_pnl'].sum()
        avg_win = df_trades[df_trades['total_pnl'] > 0]['total_pnl'].mean() if winners > 0 else 0
        avg_loss = df_trades[df_trades['total_pnl'] < 0]['total_pnl'].mean() if losers > 0 else 0
        
        max_win = df_trades['total_pnl'].max()
        max_loss = df_trades['total_pnl'].min()
        
        # Calculate drawdown
        equity_df = pd.DataFrame(self.equity_curve)
        equity_df['peak'] = equity_df['capital'].cummax()
        equity_df['drawdown'] = (equity_df['capital'] - equity_df['peak']) / equity_df['peak'] * 100
        max_drawdown = equity_df['drawdown'].min()
        
        final_capital = self.capital
        total_return = ((final_capital - self.initial_capital) / self.initial_capital) * 100
        
        return {
            "total_trades": total_trades,
            "winners": winners,
            "losers": losers,
            "win_rate": round(win_rate, 2),
            "total_pnl": round(total_pnl, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "max_win": round(max_win, 2),
            "max_loss": round(max_loss, 2),
            "initial_capital": self.initial_capital,
            "final_capital": round(final_capital, 2),
            "total_return_pct": round(total_return, 2),
            "max_drawdown_pct": round(max_drawdown, 2),
            "trades": df_trades.to_dict('records')
        }


def main():
    """Run backtest."""
    print("\n" + "=" * 60)
    print("  F&O OPTION SELLING STRATEGY - BACKTEST")
    print("=" * 60)
    
    backtester = FnOBacktester(initial_capital=100000)
    
    # Backtest Nifty 50
    print("\n📊 NIFTY 50 - 1 Year Backtest")
    print("-" * 60)
    
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
    
    results = backtester.backtest_weekly_option_selling(
        symbol="^NSEI",
        start_date=start_date,
        end_date=end_date,
        otm_pct=0.10  # 10% OTM for better premiums
    )
    
    # Print results
    print("\n" + "=" * 60)
    print("  BACKTEST RESULTS")
    print("=" * 60)
    
    if "error" in results:
        print(f"  Error: {results['error']}")
        return
    print(f"  Total Trades:     {results['total_trades']}")
    print(f"  Winners:          {results['winners']}")
    print(f"  Losers:           {results['losers']}")
    print(f"  Win Rate:         {results['win_rate']}%")
    print(f"  Total P&L:        ₹{results['total_pnl']:+,.0f}")
    print(f"  Avg Win:          ₹{results['avg_win']:,.0f}")
    print(f"  Avg Loss:         ₹{results['avg_loss']:,.0f}")
    print(f"  Max Win:          ₹{results['max_win']:,.0f}")
    print(f"  Max Loss:         ₹{results['max_loss']:,.0f}")
    print(f"  Initial Capital:  ₹{results['initial_capital']:,.0f}")
    print(f"  Final Capital:    ₹{results['final_capital']:,.0f}")
    print(f"  Total Return:     {results['total_return_pct']:+.2f}%")
    print(f"  Max Drawdown:     {results['max_drawdown_pct']:.2f}%")
    print("=" * 60)
    
    # Show last 5 trades
    print("\n  Last 5 Trades:")
    for trade in results['trades'][-5:]:
        print(f"  {trade['entry_date']} → {trade['exit_date']}: ₹{trade['total_pnl']:+,.0f} ({trade['exit_reason']})")


if __name__ == "__main__":
    main()
