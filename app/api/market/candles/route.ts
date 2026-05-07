import { NextRequest } from 'next/server';
import { fetchCandles } from '@/lib/providers/orchestrator';
import { cachedCandles, setCandles } from '@/lib/cache';

export async function GET(request: NextRequest) {
  const symbol = request.nextUrl.searchParams.get('symbol') || 'AAPL';
  const resolution = request.nextUrl.searchParams.get('resolution') || 'D';
  const count = parseInt(request.nextUrl.searchParams.get('count') || '60', 10);

  const cached = cachedCandles(symbol, resolution, count);
  if (cached) return Response.json(cached);

  try {
    const data = await fetchCandles(symbol, resolution, count);
    if (data.length) {
      setCandles(symbol, resolution, count, data);
      return Response.json(data);
    }
    return Response.json({ error: 'Candle data unavailable — try a different timeframe' }, { status: 503 });
  } catch {
    return Response.json({ error: 'Candle data unavailable — try a different timeframe' }, { status: 503 });
  }
}
