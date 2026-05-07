export async function GET() {
  const fhKey = process.env.FINNHUB_API_KEY;
  const avKey = process.env.ALPHA_VANTAGE_API_KEY;

  const checkFinnhub = async (): Promise<boolean> => {
    if (!fhKey) return false;
    const res = await fetch(
      `https://finnhub.io/api/v1/quote?symbol=AAPL&token=${fhKey}`,
      { signal: AbortSignal.timeout(5000) }
    );
    return res.ok;
  };

  const checkAV = async (): Promise<boolean> => {
    if (!avKey) return false;
    const res = await fetch(
      `https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=AAPL&apikey=${avKey}`,
      { signal: AbortSignal.timeout(5000) }
    );
    if (!res.ok) return false;
    const body = await res.json();
    return !!(body?.['Global Quote']?.['05. price']);
  };

  try {
    if (await checkFinnhub()) return Response.json({ online: true, source: 'finnhub' });
  } catch {}

  try {
    if (await checkAV()) return Response.json({ online: true, source: 'alpha-vantage' });
  } catch {}

  return Response.json({ online: false, source: null });
}
