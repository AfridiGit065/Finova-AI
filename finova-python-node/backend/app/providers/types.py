from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class NormalizedQuote(BaseModel):
    symbol: str
    price: float
    change: float
    changePercent: float
    high: float
    low: float
    open: float
    previousClose: float
    timestamp: int

class NormalizedCandle(BaseModel):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int

class NormalizedFundamentals(BaseModel):
    symbol: str
    name: str
    peRatio: float
    roe: float
    revenueCagr: float
    netMargin: float
    debtEquity: float
    marketCap: float
    score: Optional[float] = None
    verdict: Optional[str] = None
    tag: Optional[str] = None

class NormalizedNewsItem(BaseModel):
    id: str
    headline: str
    source: str
    timestamp: str
    sentiment: str  # 'Extreme Greed' | 'Greed' | 'Neutral' | 'Fear' | 'Extreme Fear'
    fearScore: int
    relatedSymbols: List[str]
    url: Optional[str] = None

class NormalizedIndicators(BaseModel):
    rsi: Optional[float] = None
    macd: Optional[Dict[str, float]] = None
    sma20: Optional[float] = None
    sma50: Optional[float] = None
    bollingerUpper: Optional[float] = None
    bollingerMiddle: Optional[float] = None
    bollingerLower: Optional[float] = None

class NormalizedKpis(BaseModel):
    marketCap: str
    sp500: str
    fearGreed: str
    vix: str
    tenYearYield: str

class NormalizedSector(BaseModel):
    name: str
    value: float
    chg: float
