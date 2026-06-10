import { fetchSectors } from '@/lib/providers/orchestrator';

export async function GET() {
  try {
    const data = await fetchSectors();
    // fetchSectors now always returns data (live or static fallback)
    return Response.json(data);
  } catch {
    return Response.json({ error: 'Sector data unavailable' }, { status: 503 });
  }
}
