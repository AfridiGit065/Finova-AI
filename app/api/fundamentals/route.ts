import { NextRequest } from 'next/server';
import { fetchFundamentals } from '@/lib/providers/orchestrator';
import { SP500_TOP100 } from '@/lib/symbols/sp500-top100';
import { SCORECARD } from '@/lib/constants';
import type { NormalizedFundamentals } from '@/lib/providers/types';

const FALLBACK_SYMBOLS = SP500_TOP100.slice(0, 8).map(s => s.sym);

/** Convert a SCORECARD entry to NormalizedFundamentals so consumers get a consistent shape. */
function scorecardToFundamentals(sym: string): NormalizedFundamentals | null {
  const s = SCORECARD[sym as keyof typeof SCORECARD];
  if (!s) return null;
  return {
    symbol: sym,
    name: s.name,
    peRatio: s.pe,
    roe: s.roe / 100,
    revenueCagr: s.cagr / 100,
    netMargin: s.margin / 100,
    debtEquity: s.de,
    marketCap: 0,
    score: s.score,
    verdict: s.verdict,
    tag: s.tag,
  };
}

async function fetchWithFallback(sym: string): Promise<NormalizedFundamentals | null> {
  const live = await fetchFundamentals(sym).catch(() => null);
  if (live) return live;
  return scorecardToFundamentals(sym);
}

export async function GET(request: NextRequest) {
  const symbol = request.nextUrl.searchParams.get('symbol');
  const symbolsParam = request.nextUrl.searchParams.get('symbols');
  const symbols = symbolsParam
    ? symbolsParam.split(',').filter(Boolean)
    : symbol
    ? [symbol]
    : FALLBACK_SYMBOLS;

  try {
    if (symbols.length === 1) {
      const data = await fetchWithFallback(symbols[0]);
      if (data) return Response.json(data);
      return Response.json({ error: `Fundamental data unavailable for ${symbols[0]}` }, { status: 503 });
    }

    const results = await Promise.allSettled(symbols.map(s => fetchWithFallback(s)));
    const data = results
      .filter((r): r is PromiseFulfilledResult<NormalizedFundamentals> =>
        r.status === 'fulfilled' && r.value !== null
      )
      .map(r => r.value);

    if (data.length === 0)
      return Response.json({ error: 'Fundamental data unavailable' }, { status: 503 });

    return Response.json(data);
  } catch {
    return Response.json({ error: 'Fundamental data unavailable' }, { status: 503 });
  }
}
