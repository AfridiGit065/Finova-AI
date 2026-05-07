import { fetchSectors } from '@/lib/providers/orchestrator';

export async function GET() {
  try {
    const data = await fetchSectors();
    if (data.length) return Response.json(data);
    return Response.json({ error: "Sector performance data unavailable — updates every 60s" }, { status: 503 });
  } catch {
    return Response.json({ error: "Sector performance data unavailable — updates every 60s" }, { status: 503 });
  }
}
