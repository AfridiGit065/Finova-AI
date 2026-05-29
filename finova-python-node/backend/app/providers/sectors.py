import asyncio
import httpx
from typing import Dict, List, Any
from app.config import FINNHUB_API_KEYS, logger

SECTOR_ETFS: Dict[str, str] = {
    'XLK': 'Technology',
    'XLV': 'Health Care',
    'XLF': 'Financials',
    'XLY': 'Consumer Discretionary',
    'XLC': 'Communication Services',
    'XLI': 'Industrials',
    'XLP': 'Consumer Staples',
    'XLE': 'Energy',
    'XLU': 'Utilities',
    'XLRE': 'Real Estate',
    'XLB': 'Materials',
}

ETF_SYMBOLS = list(SECTOR_ETFS.keys())

async def fetch_sector_performance(client: httpx.AsyncClient) -> List[Dict[str, Any]]:
    if not FINNHUB_API_KEYS:
        return []
        
    for key_index, key in enumerate(FINNHUB_API_KEYS):
        try:
            async def fetch_one(sym: str) -> Dict[str, Any]:
                url = f"https://finnhub.io/api/v1/quote?symbol={sym}&token={key}"
                res = await client.get(url, timeout=5.0)
                if res.status_code == 429:
                    raise Exception("Rate limited")
                if res.status_code != 200:
                    raise Exception(f"HTTP {res.status_code}")
                data = res.json()
                return {
                    "name": SECTOR_ETFS[sym],
                    "chg": float(data.get("dp") or 0.0)
                }

            tasks = [fetch_one(sym) for sym in ETF_SYMBOLS]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            sectors = []
            for r in results:
                if isinstance(r, dict) and r:
                    sectors.append(r)
                    
            if sectors:
                return sectors
        except Exception as e:
            logger.warning(f"Finnhub sectors fetch failed with key index {key_index}: {e}")
            continue
            
    return []
