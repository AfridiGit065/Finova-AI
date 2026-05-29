import math
import asyncio
from datetime import datetime
from fastapi import FastAPI, Request, Response, Query, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import httpx
from typing import List, Dict, Any, Optional

from app.config import (
    logger, PORT, HOST, FINNHUB_API_KEYS, ALPHA_VANTAGE_API_KEYS, GEMINI_API_KEY
)
from app.symbols import SP500_TOP100, search_local_symbols, get_all_symbols
from app.providers.types import NormalizedCandle, NormalizedFundamentals
import app.providers.orchestrator as orchestrator
import app.cache as cache
import app.copilot as copilot

# Initialize FastAPI App
app = FastAPI(
    title="Finova AI Dashboard Backend",
    description="Python FastAPI backend for Finova AI.",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared HTTP client for backend requests
client_store: Dict[str, httpx.AsyncClient] = {}

@app.on_event("startup")
async def startup_event():
    client_store["client"] = httpx.AsyncClient()
    logger.info("FastAPI Client Session Initialized")

@app.on_event("shutdown")
async def shutdown_event():
    client = client_store.get("client")
    if client:
        await client.aclose()
        logger.info("FastAPI Client Session Closed")

def get_client() -> httpx.AsyncClient:
    return client_store["client"]


# Helper for candle validation and sorting (matching lib/candleUtils.ts)
def validate_ohlc(c: NormalizedCandle) -> bool:
    o, h, l, cl = c.open, c.high, c.low, c.close
    for val in (o, h, l, cl):
        if not math.isfinite(val):
            return False
    return (
        h >= o and h >= cl and h >= l and
        l <= o and l <= cl and l <= h
    )

def process_candle_data(candles: List[NormalizedCandle]) -> List[NormalizedCandle]:
    if not candles:
        return []
    valid = [c for c in candles if validate_ohlc(c)]
    
    def parse_date(c: NormalizedCandle):
        try:
            return datetime.strptime(c.date, "%m/%d/%Y")
        except Exception:
            return datetime.fromtimestamp(0)
            
    valid.sort(key=parse_date)
    return valid

def fmt_market_cap(n: float) -> str:
    if n >= 1e12: return f"${n / 1e12:.1f}T"
    if n >= 1e9: return f"${n / 1e9:.1f}B"
    if n >= 1e6: return f"${n / 1e6:.1f}M"
    return f"${n / 1e3:.1f}K"


# Endpoints

@app.get("/api/market/status")
async def get_market_status():
    client = get_client()
    if not FINNHUB_API_KEYS:
        return {"online": False, "source": None}
        
    try:
        # Check Finnhub status using AAPL quote
        url = f"https://finnhub.io/api/v1/quote?symbol=AAPL&token={FINNHUB_API_KEYS[0]}"
        res = await client.get(url, timeout=5.0)
        if res.status_code == 200:
            return {"online": True, "source": "finnhub"}
    except Exception:
        pass
    return {"online": False, "source": None}


@app.get("/api/market/quote")
async def get_market_quote(symbols: Optional[str] = Query(None)):
    client = get_client()
    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()] if symbols else [s["sym"] for s in SP500_TOP100]
    
    try:
        data = await orchestrator.fetch_quote(client, symbol_list)
        # Match Next.js: mapping back symbols for position alignment
        enriched = []
        for i, sym in enumerate(symbol_list):
            # find match
            match = next((q for q in data if q.symbol.upper() == sym.upper()), None)
            if match:
                match_dict = match.dict()
                match_dict["symbol"] = match.symbol or sym
                match_dict["name"] = ""
                enriched.append(match_dict)
            else:
                enriched.append({
                    "symbol": sym,
                    "price": 0.0,
                    "change": 0.0,
                    "changePercent": 0.0,
                    "high": 0.0,
                    "low": 0.0,
                    "open": 0.0,
                    "previousClose": 0.0,
                    "timestamp": int(datetime.now().timestamp()),
                    "name": ""
                })
        return enriched
    except Exception as e:
        logger.error(f"Quote fetch failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Live price feed unavailable — retrying every 10s"
        )


@app.get("/api/market/candles")
async def get_market_candles(symbol: str = "AAPL"):
    client = get_client()
    symbol = symbol.upper()
    
    # L1 Cache Check
    cached_l1 = cache.get_cached("candles", symbol)
    if cached_l1:
        return cached_l1
        
    # L2 Cache Check
    cached_l2 = cache.getCachedCandles(symbol)
    if cached_l2:
        processed = [NormalizedCandle(**c) for c in cached_l2]
        sorted_candles = process_candle_data(processed)
        sorted_dicts = [c.dict() for c in sorted_candles]
        cache.set_cached("candles", symbol, sorted_dicts, 300000)  # L1 cache for 5 min
        return sorted_dicts
        
    try:
        raw_candles = await orchestrator.fetch_candles(client, symbol, "D", 100)
        sorted_candles = process_candle_data(raw_candles)
        
        if sorted_candles:
            sorted_dicts = [c.dict() for c in sorted_candles]
            cache.set_cached("candles", symbol, sorted_dicts, 300000)
            cache.set_cached_candles(symbol, sorted_dicts)
            return sorted_dicts
            
        raise HTTPException(status_code=503, detail="Candle data unavailable")
    except Exception as e:
        logger.error(f"Candles fetch error for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Candle data unavailable"
        )


@app.get("/api/market/sectors")
async def get_market_sectors():
    client = get_client()
    try:
        data = await orchestrator.fetch_sectors(client)
        if data:
            return [s.dict() for s in data]
        raise HTTPException(status_code=503, detail="Sector data unavailable")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sector data unavailable"
        )


@app.get("/api/market/indicators")
async def get_market_indicators(symbol: str = "AAPL"):
    client = get_client()
    try:
        data = await orchestrator.fetch_indicators(client, symbol)
        return data.dict()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Technical indicators temporarily unavailable"
        )


@app.get("/api/symbols")
async def get_symbols(q: Optional[str] = Query(None)):
    client = get_client()
    query = q.strip() if q else ""
    
    if query:
        if FINNHUB_API_KEYS:
            try:
                url = f"https://finnhub.io/api/v1/search?q={query}&exchange=US&token={FINNHUB_API_KEYS[0]}"
                res = await client.get(url, timeout=5.0)
                if res.status_code == 200:
                    data = res.json()
                    results = data.get("result", [])
                    matches = [
                        {"sym": s["symbol"], "name": s["description"]}
                        for s in results
                        if s.get("type") == "Common Stock"
                    ][:20]
                    if matches:
                        return matches
            except Exception:
                pass
                
        return search_local_symbols(query)
        
    return get_all_symbols()


@app.get("/api/fundamentals")
async def get_fundamentals(symbol: Optional[str] = Query(None), symbols: Optional[str] = Query(None)):
    client = get_client()
    
    symbol_list = []
    if symbols:
        symbol_list = [s.strip() for s in symbols.split(",") if s.strip()]
    elif symbol:
        symbol_list = [symbol.strip()]
    else:
        symbol_list = [s["sym"] for s in SP500_TOP100[:8]]
        
    try:
        if len(symbol_list) == 1:
            data = await orchestrator.fetch_fundamentals(client, symbol_list[0])
            if data:
                return data.dict()
            raise HTTPException(status_code=503, detail=f"Fundamental data unavailable for {symbol_list[0]}")
            
        tasks = [orchestrator.fetch_fundamentals(client, sym) for sym in symbol_list]
        results = await asyncio.gather(*tasks)
        
        valid_results = [r.dict() for r in results if r is not None]
        if not valid_results:
            raise HTTPException(status_code=503, detail="Fundamental data unavailable")
            
        return valid_results
    except Exception as e:
        logger.error(f"Fundamentals fetch error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Fundamental data unavailable"
        )


@app.get("/api/kpis")
async def get_kpis():
    cached = cache.get_cached("kpis", "response")
    if cached:
        return cached
        
    client = get_client()
    defaults = [s["sym"] for s in SP500_TOP100[:8]]
    
    try:
        # Fetch KPI bases
        kpi_task = orchestrator.fetch_kpis(client)
        # Fetch fundamentals for market cap calculation
        f_tasks = [orchestrator.fetch_fundamentals(client, sym) for sym in defaults]
        # Fetch news for composite fear/greed
        news_task = orchestrator.fetch_news(client, defaults)
        
        kpi_data, f_results, news_items = await asyncio.gather(
            kpi_task,
            asyncio.gather(*f_tasks, return_exceptions=True),
            news_task,
            return_exceptions=True
        )
        
        # Handle exceptions in gather
        if isinstance(kpi_data, Exception):
            raise kpi_data
            
        total_market_cap = 0.0
        if not isinstance(f_results, Exception):
            for f in f_results:
                if isinstance(f, NormalizedFundamentals) and f.marketCap:
                    total_market_cap += f.marketCap
                    
        avg_fear = None
        if not isinstance(news_items, Exception) and news_items:
            total_fear = sum(n.fearScore for n in news_items)
            avg_fear = round(total_fear / len(news_items))
            
        body = {
            "marketCap": fmt_market_cap(total_market_cap) if total_market_cap > 0 else "—",
            "sp500": kpi_data.sp500,
            "fearGreed": f"{100 - avg_fear} / 100" if avg_fear is not None else "—",
            "vix": kpi_data.vix,
            "tenYearYield": kpi_data.tenYearYield
        }
        
        cache.set_cached("kpis", "response", body, 25000)
        return body
    except Exception as e:
        logger.error(f"KPIs fetch error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Market KPI data unavailable — retrying every 30s"
        )


@app.get("/api/news")
async def get_news(symbols: Optional[str] = Query(None)):
    client = get_client()
    symbol_list = [s.strip() for s in symbols.split(",") if s.strip()] if symbols else [s["sym"] for s in SP500_TOP100[:8]]
    
    try:
        data = await orchestrator.fetch_news(client, symbol_list)
        if data:
            return [n.dict() for n in data]
        raise HTTPException(status_code=503, detail="News feed unavailable")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="News feed unavailable — updates every 60s"
        )


@app.post("/api/copilot")
async def post_copilot(request: Request):
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")
        
    client = get_client()
    body = await request.json()
    messages = body.get("messages", [])
    symbols = body.get("symbols", [])
    
    if not messages:
        raise HTTPException(status_code=400, detail="No messages provided")
        
    # Get last user message for entity extraction
    last_user_msg = next((m for m in reversed(messages) if m.get("role") == "user"), None)
    msg_content = last_user_msg.get("content") or "" if last_user_msg else ""
    
    tickers, intent = copilot.extract_entities(msg_content)
    context = await copilot.build_context(client, tickers, intent, symbols)
    
    return StreamingResponse(
        copilot.generate_gemini_stream(messages, context),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )


@app.post("/api/support")
async def post_support(request: Request):
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")
        
    body = await request.json()
    messages = body.get("messages", [])
    
    if not messages:
        raise HTTPException(status_code=400, detail="No messages provided")
        
    return StreamingResponse(
        copilot.generate_gemini_stream(messages, copilot.SUPPORT_SYSTEM_PROMPT),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )


@app.get("/api/settings")
async def get_settings():
    return {
        "finnhub": len(FINNHUB_API_KEYS) > 0,
        "finnhub2": len(FINNHUB_API_KEYS) > 1,
        "alphaVantage": len(ALPHA_VANTAGE_API_KEYS) > 0,
        "alphaVantage2": len(ALPHA_VANTAGE_API_KEYS) > 1,
        "alphaVantage3": len(ALPHA_VANTAGE_API_KEYS) > 2,
        "alphaVantage4": len(ALPHA_VANTAGE_API_KEYS) > 3,
        "gemini": GEMINI_API_KEY is not None
    }


@app.delete("/api/cache")
async def delete_cache():
    try:
        cleared = cache.clear_candle_cache()
        return {"ok": True, "cleared": cleared}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=True)
