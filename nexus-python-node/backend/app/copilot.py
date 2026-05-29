import re
import json
import asyncio
import httpx
import google.generativeai as genai
from typing import List, Dict, Any, Tuple, Optional

from app.config import GEMINI_API_KEY, logger
from app.symbols import get_all_symbols
import app.providers.orchestrator as orchestrator

# Initialize Gemini SDK
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

SYSTEM_PERSONA = """You are NEXUS Copilot, a financial AI assistant for the NEXUS Market Intelligence dashboard. You have access to real-time market data provided below.

NEVER:
- Make up data or metrics. Only use the information given.
- Perform tasks outside of providing financial insights based on the data.
- If asked about something you don't have data on, admit that you don't have enough information rather than guessing.

Rules:
- Ground every answer in the data provided. Do not make up metrics.
- Be concise and direct. Use **bold** for key numbers and terms.
- When asked about a stock, cite specific metrics (P/E, ROE, CAGR, margin, D/E, AI score).
- When comparing, present a balanced view of pros and cons.
- Admit when you don't have enough data rather than guessing.
- Keep responses under 250 words unless asked for detail."""

SUPPORT_SYSTEM_PROMPT = """You are the NEXUS Assistant, a helpful AI guide for a premium fintech analytics dashboard called NEXUS.

Your role is to help users navigate the dashboard and understand its features. Be friendly, concise, and direct.

Available features:
1. **Dashboard** — Market KPIs (S&P 500, VIX, Fear & Greed), top movers, sector heatmap
2. **Search** — Look up 500+ US equities by symbol or company name
3. **Compare** — Side-by-side stock comparison with radar charts and fundamental metrics
4. **Technical** — RSI, SMA (20/50), and Bollinger Bands charts for any supported ticker
5. **AI Copilot** — AI-powered fundamental analysis with live data and investment scorecards
6. **News** — Real-time headlines with market sentiment (Fear & Greed scoring)
7. **Settings** — Manage your watchlist and check API key status

Important: NEXUS is an analytics and research dashboard, NOT a brokerage. We do not support trading, deposits, wallets, or fund transfers.

Rules:
- Be helpful and friendly, but concise.
- Use **bold** for feature names and key terms.
- If asked about something outside NEXUS's scope, politely clarify what we do.
- Keep responses under 150 words unless asked for detail.
- Do not make up features or capabilities."""

def extract_entities(msg: str) -> Tuple[List[str], str]:
    lower_msg = msg.lower()
    upper_msg = msg.upper()
    
    symbols_list = get_all_symbols()
    entity_symbols = [s["sym"] for s in symbols_list]
    
    # Pre-process names to remove suffixes
    entity_names = []
    for s in symbols_list:
        clean_name = re.sub(
            r"( Inc\.| Corp\.| Corporation| Ltd\.| Co\.| plc| Group| Platforms| Technologies| Solutions)",
            "",
            s["name"],
            flags=re.IGNORECASE
        ).strip().lower()
        
        first_word = clean_name.split(" ")[0] if clean_name else ""
        entity_names.append({
            "sym": s["sym"],
            "name": clean_name,
            "first_word": first_word
        })
        
    # Match symbols (exact word boundaries)
    tickers_from_syms = []
    for sym in entity_symbols:
        if re.search(r"\b" + re.escape(sym) + r"\b", upper_msg):
            tickers_from_syms.append(sym)
            
    # Match company names
    tickers_from_names = []
    for e in entity_names:
        if e["name"] in lower_msg:
            tickers_from_names.append(e["sym"])
        elif len(e["first_word"]) > 3 and re.search(r"\b" + re.escape(e["first_word"]) + r"\b", lower_msg):
            tickers_from_names.append(e["sym"])
            
    tickers = list(set(tickers_from_syms + tickers_from_names))
    
    # Intent extraction
    if re.search(r"\b(compare|vs\.?|versus|difference|better|which)\b", lower_msg):
        intent = 'compare'
    elif re.search(r"\b(news|headline|sentiment)\b", lower_msg):
        intent = 'news'
    elif re.search(r"\b(sector|industry|market)\b", lower_msg):
        intent = 'sector'
    elif len(tickers) == 1:
        intent = 'single'
    else:
        intent = 'general'
        
    return tickers, intent

def _fundamentals_line(sym: str, f: Any) -> str:
    score_str = f"{f.score}/10" if f.score is not None else "N/A"
    verdict_str = f.verdict if f.verdict else "N/A"
    tag_str = f.tag if f.tag else "N/A"
    
    return (
        f"{f.name or sym} ({sym}): Score {score_str} · {verdict_str} · {tag_str} | "
        f"P/E {f.peRatio:.1f}× · ROE {f.roe*100:.1f}% · CAGR +{f.revenueCagr*100:.1f}% · "
        f"Margin {f.netMargin*100:.1f}% · D/E {f.debtEquity:.2f}"
    )

def _price_line(sym: str, q: Any) -> str:
    sign = "+" if q.change >= 0 else ""
    pct_sign = "+" if q.changePercent >= 0 else ""
    return f"{sym}: ${q.price:.2f} · {sign}{q.change:.2f} ({pct_sign}{q.changePercent:.2f}%)"

async def build_context(client: httpx.AsyncClient, tickers: List[str], intent: str, extra_symbols: List[str] = None) -> str:
    parts = [SYSTEM_PERSONA]
    data_parts = []
    
    all_symbols = list(set(tickers + (extra_symbols or [])))
    
    if all_symbols:
        # Fetch fundamentals and quotes concurrently
        async def safe_fetch_fundamentals(sym: str):
            try:
                return await orchestrator.fetch_fundamentals(client, sym)
            except Exception:
                return None
                
        async def safe_fetch_quote(sym: str):
            try:
                quotes = await orchestrator.fetch_quote(client, [sym])
                return quotes[0] if quotes else None
            except Exception:
                return None
                
        f_tasks = [safe_fetch_fundamentals(s) for s in all_symbols]
        q_tasks = [safe_fetch_quote(s) for s in all_symbols]
        
        f_results = await asyncio.gather(*f_tasks)
        q_results = await asyncio.gather(*q_tasks)
        
        fund_lines = []
        for i, sym in enumerate(all_symbols):
            f = f_results[i]
            if f:
                fund_lines.append(_fundamentals_line(sym, f))
        if fund_lines:
            data_parts.append("--- FUNDAMENTALS ---\n" + "\n".join(fund_lines))
            
        price_lines = []
        for i, sym in enumerate(all_symbols):
            q = q_results[i]
            if q:
                price_lines.append(_price_line(sym, q))
        if price_lines:
            data_parts.append("--- PRICE DATA ---\n" + "\n".join(price_lines))
            
    if intent == 'compare' and len(tickers) >= 2:
        data_parts.append("When comparing, highlight relative strengths, risk profiles, and which suits different investment styles.")
        
    if intent == 'news':
        try:
            # Get news
            news_items = await orchestrator.fetch_news(client, tickers if tickers else [s["sym"] for s in get_all_symbols()[:8]])
            if news_items:
                news_block = "\n".join([
                    f"[{n.sentiment}] {n.headline} ({n.source}) — Fear: {n.fearScore}/100"
                    for n in news_items
                ])
                data_parts.append("--- NEWS & SENTIMENT ---\n" + news_block)
        except Exception:
            pass
            
    if intent == 'sector' or not tickers:
        try:
            sector_data = await orchestrator.fetch_sectors(client)
            if sector_data:
                sector_block = "\n".join([
                    f"{s.name}: {'+' if s.chg >= 0 else ''}{s.chg:.2f}%"
                    for s in sector_data
                ])
                data_parts.append("--- SECTOR DATA ---\n" + sector_block)
        except Exception:
            pass
            
    if data_parts:
        parts.append("\n\n".join(data_parts))
        
    return "\n\n".join(parts)

async def generate_gemini_stream(messages: List[Dict[str, str]], system_instruction: str):
    if not GEMINI_API_KEY:
        yield f"data: {json.dumps({'error': 'GEMINI_API_KEY not configured'})}\n\n"
        yield "data: [DONE]\n\n"
        return

    # Map message roles (assistant -> model, etc.)
    contents = []
    for m in messages:
        # In route.ts, messages can have role 'bot' or 'assistant' or 'user'
        # Also supports 'text' or 'content' depending on the route (support vs copilot)
        role = "model" if m.get("role") in ("assistant", "bot", "model") else "user"
        text = m.get("content") or m.get("text") or ""
        contents.append({"role": role, "parts": [text]})
        
    try:
        # We try 'gemini-3-flash-preview' first, fallback to 'gemini-1.5-flash'
        model_name = 'gemini-3-flash-preview'
        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_instruction
            )
            # Dry run / config check or direct generation
        except Exception:
            model_name = 'gemini-1.5-flash'
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_instruction
            )
            
        config = genai.types.GenerationConfig(
            temperature=0.7,
            max_output_tokens=1024
        )
        
        response = await asyncio.to_thread(
            model.generate_content,
            contents,
            generation_config=config,
            stream=True
        )
        
        for chunk in response:
            text = chunk.text
            if not text:
                continue
            payload = {
                "candidates": [{
                    "content": {
                        "parts": [{"text": text}],
                        "role": "model"
                    }
                }]
            }
            yield f"data: {json.dumps(payload)}\n\n"
            
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        logger.error(f"Gemini streaming failed: {e}")
        payload = {"error": f"Gemini error: {str(e)}"}
        yield f"data: {json.dumps(payload)}\n\n"
        yield "data: [DONE]\n\n"
