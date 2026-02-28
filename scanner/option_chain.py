"""
Option chain scanner for Nifty & Bank Nifty
Fetches real-time option chain data from NSE/Kite
"""
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional


class OptionChainScanner:
    """Scanner for fetching option chain data."""
    
    def __init__(self, kite_client=None):
        """
        Initialize option chain scanner.
        
        Args:
            kite_client: KiteConnect instance (optional, for live data)
        """
        self.kite = kite_client
        self.nse_headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'application/json'
        }
    
    def get_spot_price(self, symbol: str) -> float:
        """
        Get current spot price of index.
        
        Args:
            symbol: "NIFTY" or "BANKNIFTY"
        
        Returns:
            Current spot price
        """
        if self.kite:
            # Use Kite for live data
            instrument = f"NSE:{symbol}"
            quote = self.kite.quote(instrument)
            return quote[instrument]['last_price']
        else:
            # Fallback to NSE (for testing)
            # In production, always use Kite for reliable data
            return self._get_nse_spot_price(symbol)
    
    def _get_nse_spot_price(self, symbol: str) -> float:
        """Fetch spot price from NSE (fallback method)."""
        # Note: NSE API may require additional authentication
        # This is a simplified version for demonstration
        try:
            url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
            response = requests.get(url, headers=self.nse_headers, timeout=10)
            data = response.json()
            return float(data['records']['underlyingValue'])
        except Exception as e:
            print(f"Error fetching NSE spot price: {e}")
            # Return approximate values for testing
            return 22000.0 if symbol == "NIFTY" else 48000.0
    
    def get_weekly_expiry(self, symbol: str) -> str:
        """
        Get next weekly expiry date.
        
        Args:
            symbol: "NIFTY" or "BANKNIFTY"
        
        Returns:
            Expiry date in format "YYYY-MM-DD"
        """
        today = datetime.now()
        
        # Nifty expires on Thursday, Bank Nifty on Wednesday
        if symbol == "NIFTY":
            target_weekday = 3  # Thursday
        else:  # BANKNIFTY
            target_weekday = 2  # Wednesday
        
        days_ahead = target_weekday - today.weekday()
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        
        expiry = today + timedelta(days=days_ahead)
        return expiry.strftime("%Y-%m-%d")
    
    def get_option_chain(self, symbol: str, expiry: str) -> Dict:
        """
        Get option chain for given symbol and expiry.
        
        Args:
            symbol: "NIFTY" or "BANKNIFTY"
            expiry: Expiry date in format "YYYY-MM-DD"
        
        Returns:
            Dict with option chain data
        """
        if self.kite:
            return self._get_kite_option_chain(symbol, expiry)
        else:
            return self._get_nse_option_chain(symbol, expiry)
    
    def _get_kite_option_chain(self, symbol: str, expiry: str) -> Dict:
        """Fetch option chain from Kite Connect."""
        # Get all instruments
        instruments = self.kite.instruments("NFO")
        
        # Filter for the symbol and expiry
        expiry_dt = datetime.strptime(expiry, "%Y-%m-%d")
        
        options = {
            "CE": {},
            "PE": {}
        }
        
        for inst in instruments:
            if (inst['name'] == symbol and 
                inst['expiry'] == expiry_dt.date() and
                inst['instrument_type'] in ['CE', 'PE']):
                
                strike = inst['strike']
                opt_type = inst['instrument_type']
                
                # Get quote
                quote = self.kite.quote(f"NFO:{inst['tradingsymbol']}")
                data = quote[f"NFO:{inst['tradingsymbol']}"]
                
                options[opt_type][strike] = {
                    "strike": strike,
                    "ltp": data['last_price'],
                    "bid": data['depth']['buy'][0]['price'] if data['depth']['buy'] else 0,
                    "ask": data['depth']['sell'][0]['price'] if data['depth']['sell'] else 0,
                    "volume": data['volume'],
                    "oi": data['oi'],
                    "tradingsymbol": inst['tradingsymbol']
                }
        
        return options
    
    def _get_nse_option_chain(self, symbol: str, expiry: str) -> Dict:
        """Fetch option chain from NSE (fallback for testing)."""
        # Simplified version - returns mock data for testing
        # In production, use Kite Connect
        spot = self.get_spot_price(symbol)
        
        options = {
            "CE": {},
            "PE": {}
        }
        
        # Generate strikes around spot (for testing)
        strikes = self._generate_strikes(spot, symbol)
        
        for strike in strikes:
            # Mock data for testing
            options["CE"][strike] = {
                "strike": strike,
                "ltp": max(1, (spot - strike) * 0.1) if spot > strike else 5,
                "bid": 0,
                "ask": 0,
                "volume": 1000,
                "oi": 5000,
                "tradingsymbol": f"{symbol}{expiry.replace('-', '')}{strike}CE"
            }
            options["PE"][strike] = {
                "strike": strike,
                "ltp": max(1, (strike - spot) * 0.1) if strike > spot else 5,
                "bid": 0,
                "ask": 0,
                "volume": 1000,
                "oi": 5000,
                "tradingsymbol": f"{symbol}{expiry.replace('-', '')}{strike}PE"
            }
        
        return options
    
    def _generate_strikes(self, spot: float, symbol: str) -> List[float]:
        """Generate strike prices around spot."""
        if symbol == "NIFTY":
            step = 50
            range_strikes = 20
        else:  # BANKNIFTY
            step = 100
            range_strikes = 20
        
        base = round(spot / step) * step
        strikes = [base + (i - range_strikes // 2) * step 
                  for i in range(range_strikes)]
        return sorted(strikes)
    
    def find_otm_strike(self, spot: float, symbol: str, option_type: str,
                       otm_percentage: float = 0.15) -> float:
        """
        Find OTM strike based on percentage.
        
        Args:
            spot: Current spot price
            symbol: "NIFTY" or "BANKNIFTY"
            option_type: "CE" or "PE"
            otm_percentage: How far OTM (default 15%)
        
        Returns:
            Strike price
        """
        if symbol == "NIFTY":
            step = 50
        else:
            step = 100
        
        if option_type == "CE":
            target = spot * (1 + otm_percentage)
        else:  # PE
            target = spot * (1 - otm_percentage)
        
        strike = round(target / step) * step
        return strike
