from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import database
from database import SessionLocal, Trade, Position, Settings
import json

app = FastAPI(title="Smart Trading Bot API", version="0.1.0")

# Allow CORS for local HTML frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def startup():
    database.init_db()

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

@app.get("/")
def read_root():
    return FileResponse("smart_trading_bot.html")

@app.get("/status")
def get_status(token: str = None, db: Session = Depends(get_db)):
    import market_data
    # Calculate simple stats
    pos_count = db.query(Position).count()
    trade_count = db.query(Trade).count()
    
    # Check data source status
    data_status = market_data.get_status(token)
    
    return {
        "running": True, 
        "positions": pos_count,
        "trades": trade_count,
        "data_source": data_status
    }

@app.get("/analyze/{symbol}")
async def analyze_symbol(symbol: str, strategy: str = "momentum", token: str = None):
    # 1. Fetch Data
    import market_data
    import strategy as strat_engine
    
    # Pass token if provided (from frontend settings)
    price = await market_data.get_price(symbol, finnhub_key=token)
    if not price:
        raise HTTPException(status_code=404, detail="Symbol not found")
        
    return {
        "symbol": symbol,
        "price": price,
        "signal": "HOLD", 
        "strategy": strategy
    }


from pydantic import BaseModel
from typing import List, Optional

@app.get("/history/{symbol}")
async def get_history(symbol: str, period: str = "1mo", interval: str = "1h"):
    import market_data
    import pandas_ta as ta
    
    df = await market_data.get_stock_candles(symbol, period=period, interval=interval)
    if df.empty:
        return []  # Return empty array instead of 404 to avoid console error spam
    
    # Calculate Indicators
    try:
        # Simple Moving Averages
        df['SMA_20'] = ta.sma(df['Close'], length=20)
        df['SMA_50'] = ta.sma(df['Close'], length=50)
        
        # MACD
        macd = ta.macd(df['Close'])
        if macd is not None:
            df = df.join(macd) # MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9
            
        # RSI
        df['RSI'] = ta.rsi(df['Close'])
        
    except Exception as e:
        print(f"Indicator error: {e}")
        
    # Format for JSON
    # Reset index to get Date/Datetime as column
    df.reset_index(inplace=True)
    
    # Handle different index names from yfinance (Date vs Datetime)
    date_col = 'Date' if 'Date' in df.columns else 'Datetime'
    
    result = []
    for _, row in df.iterrows():
        # Clean NaNs
        item = {
            "t": row[date_col].isoformat() if hasattr(row[date_col], 'isoformat') else str(row[date_col]),
            "o": float(row['Open']),
            "h": float(row['High']),
            "l": float(row['Low']),
            "c": float(row['Close']),
            "v": int(row['Volume']),
        }
        # Add indicators if present (handle NaN)
        if 'SMA_20' in row and pd.notna(row['SMA_20']): item['sma20'] = float(row['SMA_20'])
        if 'SMA_50' in row and pd.notna(row['SMA_50']): item['sma50'] = float(row['SMA_50'])
        if 'RSI' in row and pd.notna(row['RSI']): item['rsi'] = float(row['RSI'])
        # MACD keys might vary, check df columns or standard names
        # usually: MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9
        # simplified for frontend:
        if 'MACD_12_26_9' in row and pd.notna(row['MACD_12_26_9']): item['macd'] = float(row['MACD_12_26_9'])
        if 'MACDs_12_26_9' in row and pd.notna(row['MACDs_12_26_9']): item['signal'] = float(row['MACDs_12_26_9'])
        if 'MACDh_12_26_9' in row and pd.notna(row['MACDh_12_26_9']): item['hist'] = float(row['MACDh_12_26_9'])
        
        result.append(item)
        
    return result

class TradeData(BaseModel):
    symbol: str
    side: str
    qty: float
    price: float
    strategy: str = "manual"
    pnl: Optional[float] = None
    fee: Optional[float] = 0.0

@app.post("/record_trade")
def record_trade(trade: TradeData, db: Session = Depends(get_db)):
    db_trade = Trade(
        symbol=trade.symbol,
        side=trade.side,
        qty=trade.qty,
        price=trade.price,
        strategy=trade.strategy,
        pnl=trade.pnl,
        fee=trade.fee
    )
    db.add(db_trade)
    db.commit()
    return {"status": "recorded", "id": db_trade.id}

class PositionData(BaseModel):
    symbol: str
    qty: float
    avg_price: float

@app.post("/sync_positions")
def sync_positions(positions: List[PositionData], db: Session = Depends(get_db)):
    # Simple strategy: clear and replace (for now) to ensure sync
    try:
        db.query(Position).delete()
        for p in positions:
            db_pos = Position(symbol=p.symbol, qty=p.qty, avg_price=p.avg_price)
            db.add(db_pos)
        db.commit()
        return {"status": "synced", "count": len(positions)}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

