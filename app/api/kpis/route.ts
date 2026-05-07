import { fetchKpis } from '@/lib/providers/orchestrator';

export async function GET() {
  try {
    const data = await fetchKpis();
    return Response.json(data);
  } catch {
    return Response.json({ error: "Market KPI data unavailable — retrying every 30s" }, { status: 503 });
  }
}
