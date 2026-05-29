import httpx
from typing import Optional, Any, Dict, List
from app.providers.types import NormalizedFundamentals
from app.config import logger

BASE_URL = "https://api.roic.ai/v2/fundamental/ratios"

def _extract_first(data: Any) -> Optional[Dict[str, Any]]:
    if not data:
        return None
    if isinstance(data, list):
        return data[0] if len(data) > 0 else None
    if isinstance(data, dict):
        return data
    return None

async def _fetch_json(client: httpx.AsyncClient, url: str) -> Any:
    response = await client.get(url, timeout=10.0)
    if response.status_code != 200:
        raise Exception(f"Roic AI {response.status_code}: {response.text}")
    return response.json()

async def fetch_fundamentals(client: httpx.AsyncClient, symbol: str) -> Optional[NormalizedFundamentals]:
    try:
        # Fetch both profitability and credit endpoints
        profitability_url = f"{BASE_URL}/profitability/{symbol}?limit=1"
        credit_url = f"{BASE_URL}/credit/{symbol}?limit=1"
        
        # Roic AI is public, no auth keys required
        # Note: most other tickers than AAPL may return 403 or empty arrays on their free endpoint, so we catch errors.
        try:
            p_res = await _fetch_json(client, profitability_url)
            profitability_data = _extract_first(p_res)
        except Exception:
            profitability_data = None
            
        try:
            c_res = await _fetch_json(client, credit_url)
            credit_data = _extract_first(c_res)
        except Exception:
            credit_data = None
            
        if not profitability_data and not credit_data:
            return None
            
        roe = 0.0
        net_margin = 0.0
        if profitability_data:
            r_val = profitability_data.get("return_com_eqy")
            roe = float(r_val) / 100.0 if r_val is not None else 0.0
            
            m_val = profitability_data.get("profit_margin")
            net_margin = float(m_val) / 100.0 if m_val is not None else 0.0
            
        debt_equity = 0.0
        if credit_data:
            de_val = credit_data.get("tot_debt_to_tot_eqy")
            debt_equity = float(de_val) / 100.0 if de_val is not None else 0.0
            
        if not roe and not net_margin and not debt_equity:
            return None
            
        return NormalizedFundamentals(
            symbol=symbol,
            name="",
            peRatio=0.0,
            roe=roe,
            revenueCagr=0.0,
            netMargin=net_margin,
            debtEquity=debt_equity,
            marketCap=0.0
        )
    except Exception as e:
        logger.error(f"Roic AI fetch fundamentals failed for {symbol}: {e}")
        return None
