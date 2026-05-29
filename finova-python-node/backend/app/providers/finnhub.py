import asyncio
import time
from datetime import datetime, timedelta
import httpx
from typing import List, Dict, Any, Optional

from app.config import FINNHUB_API_KEYS, logger
from app.providers.types import (
    NormalizedQuote, NormalizedCandle, NormalizedFundamentals,
    NormalizedNewsItem, NormalizedIndicators, NormalizedKpis, NormalizedSector
)

BASE_URL = "https://finnhub.io/api/v1"

class FinnhubError(Exception):
    def __init__(self, message: str, status: int):
        self.message = message
        self.status = status
        super().__init__(self.message)

async def _fetch_json(client: httpx.AsyncClient, path: str, key_index: int = 0) -> Any:
    if not FINNHUB_API_KEYS:
        raise FinnhubError("No Finnhub API key configured", 401)
    
    if key_index >= len(FINNHUB_API_KEYS):
        raise FinnhubError("All Finnhub API keys rate limited", 429)
        
    key = FINNHUB_API_KEYS[key_index]
    separator = "&" if "?" in path else "?"
    url = f"{BASE_URL}{path}{separator}token={key}"
    
    try:
        response = await client.get(url, timeout=10.0)
        if response.status_code == 429:
            logger.warning(f"Finnhub rate limited for key {key_index + 1}. Rotating to next key.")
            return await _fetch_json(client, path, key_index + 1)
        if response.status_code != 200:
            raise FinnhubError(f"Finnhub {response.status_code}: {response.text}", response.status_code)
        return response.json()
    except httpx.RequestError as exc:
        raise FinnhubError(f"HTTP request failed: {exc}", 500)

async def fetch_quote(client: httpx.AsyncClient, symbols: List[str]) -> List[NormalizedQuote]:
    async def fetch_one(sym: str) -> Optional[Dict[str, Any]]:
        try:
            val = await _fetch_json(client, f"/quote?symbol={sym}")
            if val:
                return {
                    "symbol": sym,
                    "price": float(val.get("c", 0)),
                    "change": float(val.get("d", 0)),
                    "changePercent": float(val.get("dp", 0)),
                    "high": float(val.get("h", 0)),
                    "low": float(val.get("l", 0)),
                    "open": float(val.get("o", 0)),
                    "previousClose": float(val.get("pc", 0)),
                    "timestamp": int(val.get("t", int(time.time())))
                }
        except Exception:
            pass
        return None

    tasks = [fetch_one(sym) for sym in symbols]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    quotes = []
    for r in results:
        if isinstance(r, dict) and r:
            quotes.append(NormalizedQuote(**r))
    return quotes

async def fetch_candles(client: httpx.AsyncClient, symbol: str, resolution: str, count: int) -> List[NormalizedCandle]:
    to_ts = int(time.time())
    res_multiplier = {
        '1': 60, '5': 300, '15': 900, '30': 1800, '60': 3600, 'D': 86400, 'W': 604800, 'M': 2592000
    }.get(resolution, 86400)
    
    from_ts = to_ts - count * res_multiplier
    try:
        data = await _fetch_json(client, f"/stock/candle?symbol={symbol}&resolution={resolution}&from={from_ts}&to={to_ts}")
        if not data or data.get("s") == "no_data" or not data.get("t"):
            return []
        
        candles = []
        for i in range(len(data["t"])):
            dt = datetime.fromtimestamp(data["t"][i])
            date_str = dt.strftime("%m/%d/%Y")
            candles.append(NormalizedCandle(
                date=date_str,
                open=float(data["o"][i]),
                high=float(data["h"][i]),
                low=float(data["l"][i]),
                close=float(data["c"][i]),
                volume=int(data["v"][i])
            ))
        return candles
    except Exception:
        return []

async def fetch_fundamentals(client: httpx.AsyncClient, symbol: str) -> Optional[NormalizedFundamentals]:
    try:
        data = await _fetch_json(client, f"/stock/metric?symbol={symbol}&metric=all")
        m = data.get("metric") if data else None
        if not m:
            return None
        
        pe_ratio = float(m.get("peBasicExclExtraTTM") or 0)
        roe = float(m.get("roeTTM") or 0) / 100.0 if m.get("roeTTM") is not None else 0.0
        revenue_cagr = float(m.get("revenueGrowthTTMYoy") or 0) / 100.0 if m.get("revenueGrowthTTMYoy") is not None else 0.0
        net_margin = float(m.get("netProfitMarginTTM") or 0) / 100.0 if m.get("netProfitMarginTTM") is not None else 0.0
        
        debt_equity = m.get("totalDebt/totalEquityQuarterly")
        if debt_equity is None:
            debt_equity = m.get("totalDebt/totalEquityAnnual")
        debt_equity = float(debt_equity or 0)
        
        market_cap = float(m.get("marketCapitalization") or 0)
        
        if not pe_ratio and not roe and not revenue_cagr and not net_margin and not debt_equity:
            return None
            
        return NormalizedFundamentals(
            symbol=symbol,
            name="",
            peRatio=pe_ratio,
            roe=roe,
            revenueCagr=revenue_cagr,
            netMargin=net_margin,
            debtEquity=debt_equity,
            marketCap=market_cap
        )
    except Exception as e:
        logger.error(f"Finnhub fetch fundamentals failed for {symbol}: {e}")
        return None

def _score_to_sentiment(score: int) -> str:
    if score <= 15: return 'Extreme Greed'
    if score <= 35: return 'Greed'
    if score <= 55: return 'Neutral'
    if score <= 75: return 'Fear'
    return 'Extreme Fear'

def _normalize_news_item(article: Dict[str, Any]) -> NormalizedNewsItem:
    sentiment_label = str(article.get("sentiment", "")).lower()
    
    if sentiment_label in ("positive", "bullish"):
        fear_score = 15
    elif sentiment_label in ("negative", "bearish"):
        fear_score = 75
    elif sentiment_label == "neutral":
        fear_score = 50
    elif isinstance(article.get("sentimentScore"), (int, float)):
        fear_score = round((1.0 - float(article["sentimentScore"])) * 100)
    else:
        fear_score = 50
        
    ts = article.get("datetime")
    timestamp_str = (
        datetime.fromtimestamp(ts).isoformat() + "Z"
        if ts else datetime.now().isoformat() + "Z"
    )
    
    related = article.get("related", "")
    related_symbols = related.split(",") if related else []
    
    return NormalizedNewsItem(
        id=str(article.get("id") or hash(article.get("headline", ""))),
        headline=article.get("headline") or "",
        source=article.get("source") or "",
        timestamp=timestamp_str,
        sentiment=_score_to_sentiment(fear_score),
        fearScore=fear_score,
        relatedSymbols=related_symbols,
        url=article.get("url")
    )

async def fetch_news(client: httpx.AsyncClient, symbols: List[str]) -> List[NormalizedNewsItem]:
    to_dt = datetime.now()
    from_dt = to_dt - timedelta(days=7)
    
    to_str = to_dt.strftime("%Y-%m-%d")
    from_str = from_dt.strftime("%Y-%m-%d")
    
    async def fetch_one(sym: str) -> List[Dict[str, Any]]:
        try:
            return await _fetch_json(client, f"/company-news?symbol={sym}&from={from_str}&to={to_str}")
        except Exception:
            return []
            
    tasks = [fetch_one(sym) for sym in symbols]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    seen = set()
    items = []
    for res in results:
        if isinstance(res, list):
            for article in res:
                headline = article.get("headline", "")
                if not headline or headline in seen:
                    continue
                seen.add(headline)
                items.append(_normalize_news_item(article))
                
    items.sort(key=lambda x: x.fearScore, reverse=True)
    return items[:20]

async def fetch_indicators(client: httpx.AsyncClient, symbol: str) -> NormalizedIndicators:
    to_ts = int(time.time())
    from_ts = to_ts - 86400 * 60
    
    async def get_indicator(name: str, period: int) -> Optional[float]:
        try:
            data = await _fetch_json(client, f"/indicator?symbol={symbol}&resolution=D&from={from_ts}&to={to_ts}&indicator={name}&timeperiod={period}")
            vals = data.get(name)
            if vals and len(vals):
                return float(vals[-1])
        except Exception:
            pass
        return None

    # RSI, SMA20, SMA50, BBands
    async def get_bbands():
        try:
            data = await _fetch_json(client, f"/indicator?symbol={symbol}&resolution=D&from={from_ts}&to={to_ts}&indicator=bbands&timeperiod=20")
            u = data.get("upper")
            m = data.get("middle")
            l = data.get("lower")
            return (
                float(u[-1]) if u else None,
                float(m[-1]) if m else None,
                float(l[-1]) if l else None
            )
        except Exception:
            return None, None, None

    rsi, sma20, sma50, bbands = await asyncio.gather(
        get_indicator("rsi", 14),
        get_indicator("sma", 20),
        get_indicator("sma", 50),
        get_bbands()
    )
    
    return NormalizedIndicators(
        rsi=rsi,
        macd=None,
        sma20=sma20,
        sma50=sma50,
        bollingerUpper=bbands[0],
        bollingerMiddle=bbands[1],
        bollingerLower=bbands[2]
    )

async def fetch_kpis(client: httpx.AsyncClient) -> NormalizedKpis:
    async def get_val(sym: str) -> str:
        try:
            q = await _fetch_json(client, f"/quote?symbol={sym}")
            if q and q.get("c"):
                return str(q["c"])
        except Exception:
            pass
        return "—"
        
    sp, vix, tnx = await asyncio.gather(
        get_val("SPY"),
        get_val("VIX"),
        get_val("TNX")
    )
    
    return NormalizedKpis(
        marketCap="—",
        sp500=sp,
        fearGreed="—",
        vix=vix,
        tenYearYield=tnx
    )

async def fetch_sectors(client: httpx.AsyncClient) -> List[NormalizedSector]:
    try:
        data = await _fetch_json(client, "/stock/sector-performance")
        if not isinstance(data, list):
            return []
        return [
            NormalizedSector(
                name=s.get("sector") or "",
                value=0.0,
                chg=float(s.get("changes") or 0.0)
            ) for s in data
        ]
    except Exception:
        return []
