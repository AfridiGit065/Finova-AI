import { NextRequest } from 'next/server';
import { fetchFundamentals } from '@/lib/providers/orchestrator';

export async function GET(request: NextRequest) {
  const symbol = request.nextUrl.searchParams.get('symbol') || 'AAPL';
  try {
    const data = await fetchFundamentals(symbol);
    if (data) return Response.json(data);
    return Response.json({ error: `Fundamental data unavailable for ${symbol}` }, { status: 503 });
  } catch {
    return Response.json({ error: `Fundamental data unavailable for ${symbol}` }, { status: 503 });
  }
}
