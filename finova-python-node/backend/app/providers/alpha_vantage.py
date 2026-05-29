import asyncio
import httpx
from typing import List, Dict, Any, Optional

from app.config import ALPHA_VANTAGE_API_KEYS, logger
from app.providers.types import (
    NormalizedQuote, NormalizedCandle, NormalizedFundamentals,
    NormalizedIndicators, NormalizedNewsItem
)

BASE_URL = "https://www.alphavantage.co/query"

class AlphaVantageError(Exception):
    def __init__(self, message: str, status: int):
        self.message = message
        self.status = status
        super().__init__(self.message)

def _is_rate_limited(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    note = data.get("Note", "")
    info = data.get("Information", "")
    return (
        "API call frequency" in str(note) or 
        "rate limit" in str(info)
    )

async def _fetch_json(client: httpx.AsyncClient, params: Dict[str, str], key_index: int = 0) -> Any:
    if not ALPHA_VANTAGE_API_KEYS:
        raise AlphaVantageError("No API key configured", 401)
        
    if key_index >= len(ALPHA_VANTAGE_API_KEYS):
        raise AlphaVantageError("All API keys rate limited", 429)
        
    key = ALPHA_VANTAGE_API_KEYS[key_index]
    merged_params = {**params, "apikey": key}
    
    logger.warning(f"[AV] {params.get('function')} {params.get('symbol', '')} key={key_index + 1}/{len(ALPHA_VANTAGE_API_KEYS)}")
    
    try:
        response = await client.get(BASE_URL, params=merged_params, timeout=15.0)
        if response.status_code != 200:
            raise AlphaVantageError(f"Alpha Vantage {response.status_code}: {response.text}", response.status_code)
            
        data = response.json()
        if _is_rate_limited(data):
            if key_index < len(ALPHA_VANTAGE_API_KEYS) - 1:
                logger.warning(f"Alpha Vantage rate limited. Rotating to key index {key_index + 1}.")
                return await _fetch_json(client, params, key_index + 1)
            else:
                raise AlphaVantageError("All API keys rate limited", 429)
                
        if "Error Message" in data:
            raise AlphaVantageError(data["Error Message"], 400)
            
        return data
    except httpx.RequestError as exc:
        raise AlphaVantageError(f"HTTP request failed: {exc}", 500)

async def fetch_quote(client: httpx.AsyncClient, symbols: List[str]) -> List[NormalizedQuote]:
    async def fetch_one(sym: str) -> Optional[Dict[str, Any]]:
        try:
            data = await _fetch_json(client, {"function": "GLOBAL_QUOTE", "symbol": sym})
            q = data.get("Global Quote", {})
            if q:
                change_pct_str = str(q.get("10. change percent", "0")).replace("%", "")
                return {
                    "symbol": q.get("01. symbol", sym),
                    "price": float(q.get("05. price") or 0.0),
                    "change": float(q.get("09. change") or 0.0),
                    "changePercent": float(change_pct_str or 0.0),
                    "high": float(q.get("03. high") or 0.0),
                    "low": float(q.get("04. low") or 0.0),
                    "open": float(q.get("02. open") or 0.0),
                    "previousClose": float(q.get("08. previous close") or 0.0),
                    "timestamp": int(asyncio.get_event_loop().time())  # default
                }
        except Exception:
            pass
        return None

    tasks = [fetch_one(sym) for sym in symbols]
    results = await asyncio.gather(*tasks)
    
    quotes = []
    for r in results:
        if r:
            quotes.append(NormalizedQuote(**r))
    return quotes

async def fetch_candles(client: httpx.AsyncClient, symbol: str, resolution: str, count: int) -> List[NormalizedCandle]:
    try:
        # Alpha Vantage only supports daily in our fallback
        data = await _fetch_json(client, {"function": "TIME_SERIES_DAILY", "symbol": symbol, "outputsize": "compact"})
        series = data.get("Time Series (Daily)", {})
        if not series:
            return []
            
        entries = []
        for date_str, vals in series.items():
            entries.append((date_str, vals))
            
        # Sort by date chronologically
        entries.sort(key=lambda x: x[0])
        
        candles = []
        for date_str, vals in entries:
            dt = datetime_str_to_mdy(date_str)
            candles.append(NormalizedCandle(
                date=dt,
                open=float(vals.get("1. open") or 0.0),
                high=float(vals.get("2. high") or 0.0),
                low=float(vals.get("3. low") or 0.0),
                close=float(vals.get("4. close") or 0.0),
                volume=int(vals.get("5. volume") or 0)
            ))
        return candles[-count:]
    except Exception as e:
        logger.error(f"Alpha Vantage fetch candles failed for {symbol}: {e}")
        return []

def datetime_str_to_mdy(date_str: str) -> str:
    # Converts 'yyyy-mm-dd' to 'm/d/yyyy'
    try:
        parts = date_str.split("-")
        if len(parts) == 3:
            return f"{int(parts[1])}/{int(parts[2])}/{parts[0]}"
    except Exception:
        pass
    return date_str

async def fetch_fundamentals(client: httpx.AsyncClient, symbol: str) -> Optional[NormalizedFundamentals]:
    try:
        data = await _fetch_json(client, {"function": "OVERVIEW", "symbol": symbol})
        if not data or not data.get("Symbol"):
            return None
            
        pe_ratio = float(data.get("PERatio") or 0.0)
        roe = float(data.get("ReturnOnEquityTTM") or 0.0) / 100.0
        revenue_cagr = float(data.get("RevenueGrowthTTM") or 0.0) / 100.0
        net_margin = float(data.get("ProfitMargin") or 0.0) / 100.0
        debt_equity = float(data.get("DebtToEquity") or 0.0)
        market_cap = float(data.get("MarketCapitalization") or 0.0)
        
        if not pe_ratio and not roe and not revenue_cagr and not net_margin:
            return None
            
        return NormalizedFundamentals(
            symbol=symbol,
            name=data.get("Name") or "",
            peRatio=pe_ratio,
            roe=roe,
            revenueCagr=revenue_cagr,
            netMargin=net_margin,
            debtEquity=debt_equity,
            marketCap=market_cap
        )
    except Exception as e:
        logger.error(f"Alpha Vantage fetch fundamentals failed for {symbol}: {e}")
        return None

async def fetch_indicators(client: httpx.AsyncClient, symbol: str) -> NormalizedIndicators:
    async def get_indicator(func: str, key: str) -> Optional[float]:
        try:
            data = await _fetch_json(client, {
                "function": func, "symbol": symbol, "interval": "daily",
                "time_period": "14" if func == "RSI" else "20" if func == "SMA" else "50" if func == "SMA" else "20",
                "series_type": "close"
            })
            series = data.get(key, {})
            if series:
                sorted_dates = sorted(series.keys())
                if sorted_dates:
                    latest_date = sorted_dates[-1]
                    latest_vals = series[latest_date]
                    # Get first value
                    val_key = list(latest_vals.keys())[0]
                    return float(latest_vals[val_key])
        except Exception:
            pass
        return None

    # For SMA50 we need to override time_period to 50
    async def get_sma50():
        try:
            data = await _fetch_json(client, {
                "function": "SMA", "symbol": symbol, "interval": "daily",
                "time_period": "50", "series_type": "close"
            })
            series = data.get("Technical Analysis: SMA", {})
            if series:
                sorted_dates = sorted(series.keys())
                if sorted_dates:
                    latest_date = sorted_dates[-1]
                    return float(series[latest_date]["SMA"])
        except Exception:
            pass
        return None

    rsi, sma20, sma50, bbands_upper = await asyncio.gather(
        get_indicator("RSI", "Technical Analysis: RSI"),
        get_indicator("SMA", "Technical Analysis: SMA"),
        get_sma50(),
        get_indicator("BBANDS", "Technical Analysis: BBANDS")
    )
    
    return NormalizedIndicators(
        rsi=rsi,
        macd=None,
        sma20=sma20,
        sma50=sma50,
        bollingerUpper=bbands_upper,
        bollingerMiddle=None,
        bollingerLower=None
    )

async def fetch_news(client: httpx.AsyncClient, symbols: List[str]) -> List[NormalizedNewsItem]:
    return []
