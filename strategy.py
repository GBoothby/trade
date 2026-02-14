import pandas as pd
import pandas_ta as ta

def analyze(df: pd.DataFrame, strategy="momentum"):
    """
    Analyzes a DataFrame of OHLCV data.
    Returns a signal: 'BUY', 'SELL', or 'HOLD'.
    """
    if df.empty or len(df) < 50:
        return "HOLD", {}

    # Calculate indicators
    # RSI
    df['rsi'] = ta.rsi(df['Close'], length=14)
    # MACD
    macd = ta.macd(df['Close'])
    df = pd.concat([df, macd], axis=1)
    
    # Bollinger Bands
    bb = ta.bbands(df['Close'], length=20)
    df = pd.concat([df, bb], axis=1)

    # Get latest row
    row = df.iloc[-1]
    prev = df.iloc[-2]

    reason = ""
    signal = "HOLD"

    # Strategy Logic
    if strategy == "momentum":
        # RSI not overbought + MACD Crossover + Price > SMA50 (trend)
        # Simple placeholder logic
        if row['rsi'] < 70 and row['MACD_12_26_9'] > row['MACDs_12_26_9'] and prev['MACD_12_26_9'] <= prev['MACDs_12_26_9']:
            signal = "BUY"
            reason = "MACD Bullish Crossover"
        elif row['rsi'] > 70:
            signal = "SELL"
            reason = "RSI Overbought"
            
    elif strategy == "meanrevert":
        # RSI oversold < 30 -> Buy
        if row['rsi'] < 30:
            signal = "BUY"
            reason = "RSI Oversold"
        elif row['rsi'] > 70:
            signal = "SELL"
            reason = "RSI Overbought"

    return signal, {
        "rsi": row['rsi'],
        "price": row['Close'],
        "reason": reason
    }
