import { NextRequest } from 'next/server';
import { fetchNews } from '@/lib/providers/orchestrator';
import { SP500_TOP100 } from '@/lib/symbols/sp500-top100';

const FALLBACK_SYMBOLS = SP500_TOP100.slice(0, 8).map(s => s.sym);

// Server-side cache: store last successful news fetch for 5 minutes
let _newsCache: { data: any[]; expiry: number } | null = null;

export async function GET(request: NextRequest) {
  const symbols = request.nextUrl.searchParams.get('symbols')?.split(',').filter(Boolean) || FALLBACK_SYMBOLS;

  // Return cached data if still fresh
  if (_newsCache && _newsCache.expiry > Date.now()) {
    return Response.json(_newsCache.data);
  }

  try {
    const data = await fetchNews(symbols);
    if (data.length) {
      // Cache successful result for 5 min
      _newsCache = { data, expiry: Date.now() + 5 * 60 * 1000 };
      return Response.json(data);
    }
    // No new data — return stale cache or empty array (never 503)
    if (_newsCache) return Response.json(_newsCache.data);
    return Response.json([]);
  } catch {
    // On error — return stale cache or empty array gracefully
    if (_newsCache) return Response.json(_newsCache.data);
    return Response.json([]);
  }
}
