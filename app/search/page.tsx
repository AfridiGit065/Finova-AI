'use client';

import { useState } from 'react';
import { Search as SearchIcon, TrendingUp, BarChart3, ExternalLink } from 'lucide-react';
import { U, TICKERS } from '@/lib/constants';
import { GlassCard } from '@/components/shared/glass-card';
import { SectionTitle } from '@/components/shared/section-title';
import Link from 'next/link';

type Tab = 'all' | 'stocks' | 'analysis';

export default function SearchPage() {
  const [query, setQuery] = useState('');
  const [tab, setTab] = useState<Tab>('all');

  const filtered = TICKERS.filter(t =>
    t.sym.toLowerCase().includes(query.toLowerCase()) ||
    t.name.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div style={{ animation: "fi .4s ease" }}>
      <SectionTitle icon={SearchIcon}>Search</SectionTitle>

      <div style={{
        display: "flex", alignItems: "center", gap: 10,
        background: U.glass, border: `1px solid ${query ? U.cyan : U.border}`,
        borderRadius: 14, padding: "12px 16px", marginBottom: 16,
        transition: "all .2s"
      }}>
        <SearchIcon size={16} color={query ? U.cyan : U.textMute} />
        <input
          value={query} onChange={e => setQuery(e.target.value)}
          placeholder="Search across 8 tracked symbols..."
          style={{
            flex: 1, background: "transparent", border: "none", outline: "none",
            color: U.text, fontSize: 14, lineHeight: 1.5
          }}
        />
        {query && (
          <span style={{ fontSize: 11, color: U.textMute, background: U.glassLo, padding: "3px 10px", borderRadius: 999 }}>
            {filtered.length} results
          </span>
        )}
      </div>

      <div style={{ display: "flex", gap: 6, marginBottom: 16 }}>
        {(['all', 'stocks', 'analysis'] as Tab[]).map(t => (
          <button key={t} onClick={() => setTab(t)} style={{
            padding: "6px 14px", borderRadius: 999, border: `1px solid ${tab === t ? U.cyan : U.border}`,
            background: tab === t ? U.cyanSoft : U.glassLo, color: tab === t ? U.cyan : U.textDim,
            fontSize: 11, fontWeight: 600, cursor: "pointer", transition: "all .15s"
          }}>{t === 'all' ? 'All' : t === 'stocks' ? 'Stocks' : 'Analysis'}</button>
        ))}
      </div>

      {filtered.length === 0 && query && (
        <GlassCard style={{ padding: "32px", textAlign: "center" }}>
          <div style={{ fontSize: 13, color: U.textMute }}>No results for &quot;{query}&quot;</div>
          <div style={{ fontSize: 11, color: U.textFaint, marginTop: 4 }}>Try a ticker symbol like AAPL or a company name</div>
        </GlassCard>
      )}

      {filtered.length === 0 && !query && (
        <GlassCard style={{ padding: "40px 24px", textAlign: "center" }}>
          <div style={{ width: 56, height: 56, borderRadius: "50%", background: U.glass, border: `1px solid ${U.border}`, display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto 16px" }}>
            <SearchIcon size={22} color={U.textMute} />
          </div>
          <div style={{ fontSize: 15, fontWeight: 700, color: U.text, marginBottom: 6 }}>Search across 8 tracked symbols</div>
          <div style={{ fontSize: 12, color: U.textMute, lineHeight: 1.6 }}>Type a ticker or company name to find fundamentals, charts, and AI analysis.</div>
          <div style={{ display: "flex", gap: 6, justifyContent: "center", flexWrap: "wrap", marginTop: 16 }}>
            {TICKERS.map(t => (
              <span key={t.sym} style={{ background: U.glassLo, color: U.textDim, padding: "4px 12px", borderRadius: 999, fontSize: 11, fontWeight: 600, border: `1px solid ${U.border}` }}>{t.sym}</span>
            ))}
          </div>
        </GlassCard>
      )}

      {filtered.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
          {filtered.map(t => (
            <Link key={t.sym} href="/compare" style={{ textDecoration: "none" }}>
              <GlassCard style={{ padding: "14px 18px", display: "flex", alignItems: "center", gap: 14, cursor: "pointer" }}>
                <div style={{
                  width: 38, height: 38, borderRadius: 10,
                  background: `linear-gradient(135deg,${U.cyanSoft},${U.violetSoft})`,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  border: `1px solid ${U.borderHi}`, flexShrink: 0
                }}>
                  <TrendingUp size={16} color={U.cyan} />
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span style={{ fontSize: 14, fontWeight: 700, color: U.text }}>{t.sym}</span>
                    <span style={{ fontSize: 11, color: U.textMute }}>{t.name}</span>
                  </div>
                  <div style={{ display: "flex", gap: 12, marginTop: 4 }}>
                    <span style={{ fontSize: 10, color: U.textFaint, display: "flex", alignItems: "center", gap: 4 }}>
                      <BarChart3 size={10} /> View comparison
                    </span>
                    <span style={{ fontSize: 10, color: U.textFaint, display: "flex", alignItems: "center", gap: 4 }}>
                      <ExternalLink size={10} /> Full analysis
                    </span>
                  </div>
                </div>
                <span style={{ fontSize: 12, fontWeight: 700, color: t.pct >= 0 ? U.up : U.down, fontFamily: 'JetBrains Mono' }}>
                  {t.pct >= 0 ? '+' : ''}{t.pct}%
                </span>
              </GlassCard>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
