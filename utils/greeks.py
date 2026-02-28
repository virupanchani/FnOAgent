"""
Greeks calculator for options using Black-Scholes model
"""
import numpy as np
from scipy.stats import norm
from datetime import datetime


def calculate_greeks(spot: float, strike: float, time_to_expiry: float, 
                    volatility: float, risk_free_rate: float = 0.07,
                    option_type: str = "CE") -> dict:
    """
    Calculate option Greeks using Black-Scholes model.
    
    Args:
        spot: Current price of underlying
        strike: Strike price
        time_to_expiry: Time to expiry in years
        volatility: Implied volatility (annualized)
        risk_free_rate: Risk-free rate (default 7% for India)
        option_type: "CE" for Call or "PE" for Put
    
    Returns:
        dict with delta, gamma, theta, vega, rho
    """
    if time_to_expiry <= 0:
        return {
            "delta": 0, "gamma": 0, "theta": 0, 
            "vega": 0, "rho": 0, "premium": 0
        }
    
    # Black-Scholes parameters
    d1 = (np.log(spot / strike) + (risk_free_rate + 0.5 * volatility ** 2) * time_to_expiry) / \
         (volatility * np.sqrt(time_to_expiry))
    d2 = d1 - volatility * np.sqrt(time_to_expiry)
    
    # Calculate Greeks
    if option_type == "CE":
        delta = norm.cdf(d1)
        premium = spot * norm.cdf(d1) - strike * np.exp(-risk_free_rate * time_to_expiry) * norm.cdf(d2)
    else:  # PE
        delta = -norm.cdf(-d1)
        premium = strike * np.exp(-risk_free_rate * time_to_expiry) * norm.cdf(-d2) - spot * norm.cdf(-d1)
    
    gamma = norm.pdf(d1) / (spot * volatility * np.sqrt(time_to_expiry))
    vega = spot * norm.pdf(d1) * np.sqrt(time_to_expiry) / 100  # Per 1% change in IV
    theta = (-spot * norm.pdf(d1) * volatility / (2 * np.sqrt(time_to_expiry)) - 
             risk_free_rate * strike * np.exp(-risk_free_rate * time_to_expiry) * norm.cdf(d2 if option_type == "CE" else -d2)) / 365
    
    if option_type == "CE":
        rho = strike * time_to_expiry * np.exp(-risk_free_rate * time_to_expiry) * norm.cdf(d2) / 100
    else:
        rho = -strike * time_to_expiry * np.exp(-risk_free_rate * time_to_expiry) * norm.cdf(-d2) / 100
    
    return {
        "delta": round(delta, 4),
        "gamma": round(gamma, 6),
        "theta": round(theta, 2),
        "vega": round(vega, 2),
        "rho": round(rho, 2),
        "premium": round(premium, 2)
    }


def days_to_expiry(expiry_date: str) -> float:
    """
    Calculate days to expiry from expiry date string.
    
    Args:
        expiry_date: Expiry date in format "YYYY-MM-DD"
    
    Returns:
        Time to expiry in years
    """
    expiry = datetime.strptime(expiry_date, "%Y-%m-%d")
    today = datetime.now()
    days = (expiry - today).days
    return max(days / 365.0, 0)


def estimate_implied_volatility(spot: float, strike: float, premium: float,
                                time_to_expiry: float, option_type: str = "CE",
                                risk_free_rate: float = 0.07) -> float:
    """
    Estimate implied volatility using Newton-Raphson method.
    
    Args:
        spot: Current price of underlying
        strike: Strike price
        premium: Market price of option
        time_to_expiry: Time to expiry in years
        option_type: "CE" for Call or "PE" for Put
        risk_free_rate: Risk-free rate
    
    Returns:
        Implied volatility (annualized)
    """
    # Initial guess
    iv = 0.3
    max_iterations = 100
    tolerance = 0.0001
    
    for _ in range(max_iterations):
        greeks = calculate_greeks(spot, strike, time_to_expiry, iv, risk_free_rate, option_type)
        price_diff = greeks["premium"] - premium
        
        if abs(price_diff) < tolerance:
            return round(iv, 4)
        
        # Newton-Raphson update
        vega = greeks["vega"] * 100  # Convert back to per 100% change
        if vega == 0:
            break
        
        iv = iv - price_diff / vega
        
        # Keep IV in reasonable bounds
        iv = max(0.01, min(iv, 2.0))
    
    return round(iv, 4)
