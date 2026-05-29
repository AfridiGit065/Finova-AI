'use client';

import { U } from '@/lib/constants';

interface ScoreBadgeProps {
  score: number;
  isWinner?: boolean;
}

export function ScoreBadge({ score, isWinner = false }: ScoreBadgeProps) {
  const [fg, tint] =
    score >= 8 ? [U.emerald, "var(--score-high-bg)"] :
      score >= 6 ? [U.cyan, "var(--score-mid-bg)"] :
        score >= 4 ? [U.amber, "var(--score-amber-bg)"] :
          [U.rose, "var(--score-low-bg)"];

  return (
    <div style={{
      borderRadius: 12, padding: "8px 12px", textAlign: "center", minWidth: 50, flexShrink: 0,
      background: tint,
    }}>
      <div style={{ fontSize: 20, fontWeight: 700, color: fg, fontFamily: "'Inter',sans-serif", lineHeight: 1, letterSpacing: "-0.03em" }}>{score}</div>
      <div style={{ fontSize: 8, color: fg, marginTop: 3, fontWeight: 500, letterSpacing: "0.08em", opacity: .5 }}>/10</div>
    </div>
  );
}
