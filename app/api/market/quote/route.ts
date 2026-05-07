import { NextRequest } from 'next/server';
import { fetchQuote } from '@/lib/providers/orchestrator';
import { DEFAULT_SYMBOLS } from '@/lib/providers/types';

export async function GET(request: NextRequest) {
  const symbols = request.nextUrl.searchParams.get('symbols')?.split(',').filter(Boolean) || DEFAULT_SYMBOLS;
  try {
    const data = await fetchQuote(symbols);
    const enriched = data.map((q, i) => ({
      ...q,
      symbol: q.symbol || symbols[i] || '',
      name: '',
    }));
    return Response.json(enriched);
  } catch {
    return Response.json(
      { error: 'Live price feed unavailable — retrying every 10s' },
      { status: 503 }
    );
  }
}
