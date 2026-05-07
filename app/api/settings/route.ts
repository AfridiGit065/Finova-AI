export async function GET() {
  return Response.json({
    finnhub: !!process.env.FINNHUB_API_KEY,
    alphaVantage: !!process.env.ALPHA_VANTAGE_API_KEY,
    gemini: !!process.env.GEMINI_API_KEY,
  });
}
