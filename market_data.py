import yfinance as yf
import ccxt.async_support as ccxt
import pandas as pd
import aiohttp
import asyncio

import os
import requests_cache
from datetime import timedelta

# Cache for minimal API calls (internal)
_cache = {}

# Cached session for historical data only (avoid rate limits on charts)
cached_session = requests_cache.CachedSession('yfinance.cache', expire_after=timedelta(minutes=30))

def get_status(provided_key: str = None):
    key = provided_key or os.environ.get("FINNHUB_KEY")
    if key:
        return "Live (Finnhub)"
    return "Live (YFinance)"

async def get_stock_price(symbol: str, finnhub_key: str = None):
    # 0. Resolve Key (passed > env)
    key = finnhub_key or os.environ.get("FINNHUB_KEY")
    
    # 1. Try Finnhub if key provided (Real-time IEX data)
    if key:
        try:
            async with aiohttp.ClientSession() as sess:
                url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={key}"
                async with sess.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        price = data.get('c', 0)
                        if price > 0: return price
        except Exception as e:
            print(f"Finnhub error {symbol}: {e}")

    # 2. Fallback to yfinance (no cache – fresh prices for scanning)
    try:
        ticker = yf.Ticker(symbol)
        # fast fetch of current price
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
    # Retry with backoff to handle Yahoo rate limiting
    for attempt in range(3):
        try:
            ticker = yf.Ticker(symbol, session=cached_session)
            df = ticker.history(period=period, interval=interval)
            if not df.empty:
                return df
            # Empty df might mean rate limited, retry after delay
            if attempt < 2:
                await asyncio.sleep(2 * (attempt + 1))
        except Exception as e:
            print(f"Error fetching candles {symbol} (attempt {attempt+1}): {e}")
            if attempt < 2:
                await asyncio.sleep(2 * (attempt + 1))
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
