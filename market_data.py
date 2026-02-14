import yfinance as yf
import ccxt.async_support as ccxt
import pandas as pd
import aiohttp
import asyncio

import os

# Cache for minimal API calls
_cache = {}

def get_status(provided_key: str = None):
    key = provided_key or os.environ.get("FINNHUB_KEY")
    if key:
        return "Live (Finnhub)"
    return "Delayed (YFinance)"

async def get_stock_price(symbol: str, finnhub_key: str = None):
    # 0. Resolve Key (passed > env)
    key = finnhub_key or os.environ.get("FINNHUB_KEY")
    
    # 1. Try Finnhub if key provided (Real-time IEX data)
    if key:
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={key}"
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        price = data.get('c', 0)
                        if price > 0: return price
        except Exception as e:
            print(f"Finnhub error {symbol}: {e}")

    # 2. Fallback to yfinance (Delayed ~15m usually, but reliable)
    try:
        ticker = yf.Ticker(symbol)
        # fast fetch of current price
        # 'regularMarketPrice' often faster than history
        info = ticker.fast_info
        if info and info.last_price:
             return info.last_price
             
        todays_data = ticker.history(period='1d')
        if not todays_data.empty:
            return todays_data['Close'].iloc[-1]
    except Exception as e:
        print(f"yfinance fetch error {symbol}: {e}")
    return None

async def get_stock_candles(symbol: str, period="1mo", interval="1h"):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        return df
    except Exception as e:
        print(f"Error fetching candles {symbol}: {e}")
        return pd.DataFrame()

# Crypto (Binance public)
exchange = ccxt.binance()

async def get_crypto_price(symbol: str):
    # ccxt expects 'BTC/USDT', our app uses 'BTC-USD' or 'BTCUSDT'
    # Map 'BTC-USD' -> 'BTC/USDT'
    pair = symbol.replace("-USD", "/USDT").replace("USD", "/USDT") # simple heuristic
    if "/" not in pair: pair = f"{symbol}/USDT" 
    
    try:
        ticker = await exchange.fetch_ticker(pair)
        return ticker['last']
    except Exception as e:
        print(f"Error fetching crypto {symbol}: {e}")
    return None

async def get_price(symbol: str, finnhub_key: str = None):
    if "-" in symbol or "USD" in symbol and not symbol.startswith("USD"): 
        # assume crypto if has dash or ends in USD (like BTC-USD)
        return await get_crypto_price(symbol)
    return await get_stock_price(symbol, finnhub_key)

async def close():
    await exchange.close()
