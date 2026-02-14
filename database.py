from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

DATABASE_URL = "sqlite:///./trades.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Trade(Base):
    __tablename__ = "trades"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True)
    side = Column(String)  # BUY / SELL
    qty = Column(Float)
    price = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    strategy = Column(String)
    pnl = Column(Float, nullable=True)
    fee = Column(Float, default=0.0)

class Position(Base):
    __tablename__ = "positions"
    symbol = Column(String, primary_key=True, index=True)
    qty = Column(Float)
    avg_price = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

class Settings(Base):
    __tablename__ = "settings"
    key = Column(String, primary_key=True, index=True)
    value = Column(String) # JSON encoded string

def init_db():
    Base.metadata.create_all(bind=engine)
