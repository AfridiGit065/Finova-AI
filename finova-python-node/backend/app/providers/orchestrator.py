import httpx
from typing import List, Dict, Any, Optional

from app.providers.types import (
    NormalizedQuote, NormalizedCandle, NormalizedFundamentals,
    NormalizedNewsItem, NormalizedIndicators, NormalizedKpis, NormalizedSector
)
import app.providers.finnhub as fh
import app.providers.alpha_vantage as av
import app.providers.roic_ai as roic
import app.providers.sectors as sectors_provider
from app.config import logger

def clamp(v: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(max_val, v))

def compute_scorecard_inplace(f: NormalizedFundamentals) -> None:
    pe = f.peRatio
    roe_pct = f.roe * 100
    cagr_pct = f.revenueCagr * 100
    margin_pct = f.netMargin * 100
    de = f.debtEquity

    val = clamp(100 - pe * 0.8, 5.0, 95.0)
    prof = clamp(roe_pct * 0.3 + margin_pct * 0.7, 5.0, 95.0)
    growth = clamp(cagr_pct * 3 + 15, 5.0, 95.0)
    health = clamp(100 - min(de, 6.0) * 10, 5.0, 95.0)
    mom = clamp(growth * 0.5 + val * 0.3 + prof * 0.2, 5.0, 95.0)
    sent = clamp(prof * 0.5 + health * 0.5, 5.0, 95.0)

    raw_score = (val * 0.05 + prof * 0.25 + growth * 0.20 + health * 0.20 + mom * 0.15 + sent * 0.15) / 10.0
    score = clamp(round(raw_score * 10) / 10.0, 1.0, 10.0)

    if score >= 9.0:
        verdict = 'Strong Buy Signal'
    elif score >= 7.5:
        verdict = 'Wise to Invest'
    elif score >= 6.5:
        verdict = 'Cautious Buy'
    elif score >= 5.0:
        verdict = 'Proceed with Caution'
    else:
        verdict = 'Avoid'

    dims = [
        ('High Growth', growth),
        ('Margin Power', prof),
        ('Value Growth', val),
        ('Stable Growth', health),
    ]
    dims.sort(key=lambda x: x[1], reverse=True)
    tag = dims[0][0]

    f.score = score
    f.verdict = verdict
    f.tag = tag

async def fallback(primary, secondary):
    try:
        res = await primary()
        if res is not None:
            return res
    except Exception:
        pass
    return await secondary()

async def fetch_quote(client: httpx.AsyncClient, symbols: List[str]) -> List[NormalizedQuote]:
    return await fallback(
        lambda: fh.fetch_quote(client, symbols),
        lambda: av.fetch_quote(client, symbols)
    )

async def fetch_candles(client: httpx.AsyncClient, symbol: str, resolution: str, count: int) -> List[NormalizedCandle]:
    return await av.fetch_candles(client, symbol, resolution, count)

async def fetch_fundamentals(client: httpx.AsyncClient, symbol: str) -> Optional[NormalizedFundamentals]:
    # 1. Try Finnhub
    fh_res = None
    try:
        fh_res = await fh.fetch_fundamentals(client, symbol)
    except Exception:
        pass
        
    if fh_res:
        # Fill gaps using Roic AI (roe, netMargin, debtEquity)
        try:
            roic_res = await roic.fetch_fundamentals(client, symbol)
            if roic_res:
                fh_res.roe = fh_res.roe or roic_res.roe
                fh_res.netMargin = fh_res.netMargin or roic_res.netMargin
                fh_res.debtEquity = fh_res.debtEquity or roic_res.debtEquity
        except Exception:
            pass
        compute_scorecard_inplace(fh_res)
        return fh_res
        
    # 2. Try Fallback: Alpha Vantage -> Roic AI
    async def primary_av():
        av_res = await av.fetch_fundamentals(client, symbol)
        if av_res:
            compute_scorecard_inplace(av_res)
        return av_res
        
    async def secondary_roic():
        roic_res = await roic.fetch_fundamentals(client, symbol)
        if roic_res:
            compute_scorecard_inplace(roic_res)
        return roic_res
        
    return await fallback(primary_av, secondary_roic)

async def fetch_news(client: httpx.AsyncClient, symbols: List[str]) -> List[NormalizedNewsItem]:
    return await fh.fetch_news(client, symbols)

async def fetch_indicators(client: httpx.AsyncClient, symbol: str) -> NormalizedIndicators:
    return await av.fetch_indicators(client, symbol)

async def fetch_kpis(client: httpx.AsyncClient) -> NormalizedKpis:
    return await fh.fetch_kpis(client)

async def fetch_sectors(client: httpx.AsyncClient) -> List[NormalizedSector]:
    # Try sectors performance using ETF Quotes
    try:
        etf_sectors = await sectors_provider.fetch_sector_performance(client)
        if etf_sectors:
            return [
                NormalizedSector(name=s["name"], value=0.0, chg=s["chg"])
                for s in etf_sectors
            ]
    except Exception:
        pass
        
    # Fallback to Finnhub /stock/sector-performance
    try:
        return await fh.fetch_sectors(client)
    except Exception:
        return []
