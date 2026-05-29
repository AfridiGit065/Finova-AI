'use client';

import { useState } from 'react';
import { ChevronRight, ChevronDown } from 'lucide-react';
import { U, fmt } from '@/lib/constants';
import type { ScorecardData } from '@/lib/scorecard-utils';
import { ScoreBadge } from './score-badge';

interface ScoreCardProps {
  ticker: string;
  data: ScorecardData;
  expanded: boolean;
  onToggle: () => void;
}

function generateCoach(d: ScorecardData, ticker: string): string {
  const peStr = d.pe ? `${d.pe.toFixed(1)}\u00d7` : 'N/A';
  const marginStr = d.margin ? `${d.margin}%` : 'N/A';
  const cagrStr = d.cagr ? `${d.cagr}%` : 'N/A';
  const roeStr = d.roe ? `${d.roe}%` : 'N/A';
  const deStr = d.de ? `${d.de.toFixed(2)}\u00d7` : 'N/A';
  const marginDesc = d.margin > 35 ? 'exceptional' : d.margin > 20 ? 'strong' : d.margin > 10 ? 'healthy' : d.margin ? 'moderate' : 'unavailable';
  const growthDesc = d.cagr > 50 ? 'exceptional' : d.cagr > 20 ? 'strong' : d.cagr > 10 ? 'steady' : d.cagr > 5 ? 'moderate' : d.cagr ? 'slowing' : 'unavailable';
  const debtDesc = d.de < 0.3 ? 'minimal' : d.de < 1 ? 'conservative' : d.de < 2 ? 'moderate' : d.de ? 'elevated' : 'unavailable';
  const valDesc = d.pe < 15 ? 'attractive' : d.pe < 25 ? 'fair' : d.pe < 40 ? 'premium' : d.pe ? 'stretched' : 'unavailable';
  return `${d.name} shows a ${d.verdict.toLowerCase()} signal with AI Score ${d.score}/10. At ${peStr} P/E (${valDesc}), the ${d.tag.toLowerCase()} profile is supported by ${marginDesc} margins (${marginStr}) and ${growthDesc} revenue growth (${cagrStr} CAGR). ROE of ${roeStr} and ${debtDesc} leverage (${deStr} D/E) suggest ${d.roe > 30 ? 'efficient capital deployment' : 'room for operational improvement'}. Position sizing should reflect the ${d.score >= 7.5 ? 'favorable' : 'cautious'} risk/reward profile.`;
}

const tagColors: Record<string, string> = {
  'High Growth':  'var(--emerald)',
  'Margin Power': 'var(--violet)',
  'Value Growth': 'var(--cyan)',
  'Stable Growth':'var(--amber)',
};

export function ScoreCard({ ticker, data, expanded, onToggle }: ScoreCardProps) {
  const [h, sh] = useState(false);
  const coachText = generateCoach(data, ticker);
  const dotColor = tagColors[data.tag] || U.cyan;

  return (
    <div
      onMouseEnter={() => sh(true)}
      onMouseLeave={() => sh(false)}
      onClick={onToggle}
      style={{
        marginBottom: 8, cursor: "pointer",
        borderRadius: 12, transition: "all .25s",
        background: h ? "var(--glass-hi)" : U.cardBg,
        boxShadow: U.cardShadow,
        border: h ? "1px solid rgba(255,255,255,0.1)" : U.cardBorder,
        backdropFilter: "blur(12px)", WebkitBackdropFilter: "blur(12px)",
      }}
    >
      <div style={{ padding: 16, display: "flex", alignItems: "center", gap: 12 }}>
        <ScoreBadge score={data.score} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 600, color: U.text, fontSize: 14, fontFamily: "'Inter',sans-serif", letterSpacing: "-0.02em" }}>{ticker}</div>
          <div style={{ fontSize: 11, color: U.textDim, marginTop: 2, fontWeight: 400 }}>{data.verdict}</div>
        </div>
        <span style={{
          fontSize: 11, color: U.textDim, fontWeight: 500, flexShrink: 0,
          display: "flex", alignItems: "center", gap: 5
        }}>
          <span style={{ width: 5, height: 5, borderRadius: "50%", background: dotColor, display: "inline-block", flexShrink: 0 }} />
          {data.tag}
        </span>
        {expanded ? <ChevronDown size={13} color={U.textMute} /> : <ChevronRight size={13} color={U.textMute} />}
      </div>
      {expanded && (
        <div style={{ borderTop: "1px solid rgba(255,255,255,0.05)", padding: "16px", animation: "fi .22s ease" }}>
          <div style={{ display: "grid", gridTemplateColumns: "var(--grid-3)" as any, gap: 8, marginBottom: 12 }}>
            {[
              { l: "P/E Ratio", v: fmt(data.pe) + "\u00d7", n: data.pe < 35 ? "Fairly Valued" : "Premium" },
              { l: "ROE", v: fmt(data.roe) + "%", n: data.roe > 30 ? "Exceptional" : "Average" },
              { l: "Rev CAGR", v: "+" + fmt(data.cagr) + "%", n: data.cagr > 20 ? "High Growth" : "Stable" },
              { l: "Net Margin", v: fmt(data.margin) + "%", n: data.margin > 20 ? "Strong" : "Moderate" },
              { l: "D/E Ratio", v: fmt(data.de, 2) + "\u00d7", n: data.de < 1 ? "Low Leverage" : "Leveraged" },
              { l: "AI Score", v: data.score + "/10", n: data.verdict },
            ].map(m => (
              <div key={m.l} style={{ background: U.cardBg, borderRadius: 10, padding: "10px 12px", boxShadow: U.cardShadow, border: U.cardBorder }}>
                <div style={{
                  fontSize: 9, color: U.textMute, fontWeight: 600,
                  textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 4
                }}>{m.l}</div>
                <div style={{ fontSize: 14, fontWeight: 600, color: U.text, fontFamily: "'JetBrains Mono',monospace" }}>{m.v}</div>
                <div style={{ fontSize: 9, color: U.textDim, marginTop: 3 }}>{m.n}</div>
              </div>
            ))}
          </div>
          <div style={{
            fontSize: 12, color: U.textDim, lineHeight: 1.7, padding: "14px 16px",
            background: U.cardBg, borderRadius: 10,
            borderLeft: `3px solid ${U.cyan}`, boxShadow: U.cardShadow,
          }}>
            <strong style={{ color: U.text, fontWeight: 600 }}>AI Coach: </strong>{coachText}
          </div>
        </div>
      )}
    </div>
  );
}
