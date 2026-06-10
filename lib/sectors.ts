const SECTOR_ETFS: Record<string, string> = {
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
};

const ETF_SYMBOLS = Object.keys(SECTOR_ETFS);

// Static fallback — approximate recent values, shown when all APIs fail
const STATIC_SECTOR_FALLBACK: { name: string; chg: number }[] = [
  { name: 'Technology',             chg:  1.24 },
  { name: 'Health Care',            chg: -0.38 },
  { name: 'Financials',             chg:  0.67 },
  { name: 'Consumer Discretionary', chg:  0.92 },
  { name: 'Communication Services', chg:  1.05 },
  { name: 'Industrials',            chg:  0.31 },
  { name: 'Consumer Staples',       chg: -0.14 },
  { name: 'Energy',                 chg: -1.22 },
  { name: 'Utilities',              chg: -0.55 },
  { name: 'Real Estate',            chg:  0.18 },
  { name: 'Materials',              chg: -0.29 },
];

// In-memory cache: 10 min TTL
let _sectorCache: { data: { name: string; chg: number }[]; expiry: number } | null = null;

export async function fetchSectorPerformance(): Promise<{ name: string; chg: number }[]> {
  // Return from cache if still valid
  if (_sectorCache && _sectorCache.expiry > Date.now()) {
    return _sectorCache.data;
  }

  const keys = [
    process.env.FINNHUB_API_KEY,
    process.env.FINNHUB_API_KEY_2,
  ].filter(Boolean) as string[];

  if (keys.length > 0) {
    for (const key of keys) {
      try {
        const results = await Promise.allSettled(
          ETF_SYMBOLS.map(sym =>
            fetch(`https://finnhub.io/api/v1/quote?symbol=${sym}&token=${key}`, { next: { revalidate: 60 } } as any)
              .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
              .then(d => ({ name: SECTOR_ETFS[sym], chg: d.dp ?? 0 }))
          )
        );
        const sectors = results
          .filter((r): r is PromiseFulfilledResult<{ name: string; chg: number }> =>
            r.status === 'fulfilled' && r.value != null
          )
          .map(r => r.value);

        if (sectors.length > 0) {
          _sectorCache = { data: sectors, expiry: Date.now() + 10 * 60 * 1000 };
          return sectors;
        }
      } catch {
        continue;
      }
    }
  }

  // Return cached stale data if available, otherwise static fallback
  if (_sectorCache) return _sectorCache.data;
  return STATIC_SECTOR_FALLBACK;
}
