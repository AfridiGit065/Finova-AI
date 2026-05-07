import { NextRequest } from 'next/server';
import { fetchNews } from '@/lib/providers/orchestrator';
import { TICKERS } from '@/lib/constants';

export async function GET(request: NextRequest) {
  const symbols = request.nextUrl.searchParams.get('symbols')?.split(',').filter(Boolean) || TICKERS.map(t => t.sym);
  try {
    const data = await fetchNews(symbols);
    if (data.length) return Response.json(data);
    return Response.json({ error: 'News feed unavailable — updates every 60s' }, { status: 503 });
  } catch {
    return Response.json({ error: 'News feed unavailable — updates every 60s' }, { status: 503 });
  }
}
