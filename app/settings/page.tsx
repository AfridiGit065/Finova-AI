'use client';

import { useState, useEffect } from 'react';
import { Settings as SettingsIcon, Server, Palette, CheckCircle, XCircle } from 'lucide-react';
import { U } from '@/lib/constants';
import { GlassCard } from '@/components/shared/glass-card';
import { SectionTitle } from '@/components/shared/section-title';

export default function SettingsPage() {
  const [conn, setConn] = useState<Record<string, boolean>>({});

  useEffect(() => {
    fetch('/api/settings').then(r => r.json()).then(setConn).catch(() => {});
  }, []);

  const connections = [
    { name: 'Finnhub', ok: conn.finnhub, label: 'Market data (primary)' },
    { name: 'Alpha Vantage', ok: conn.alphaVantage, label: 'Market data (fallback)' },
    { name: 'Gemini AI', ok: conn.gemini, label: 'AI Copilot' },
  ];

  return (
    <div style={{ animation: "fi .4s ease", maxWidth: 640 }}>
      <SectionTitle icon={SettingsIcon}>Settings</SectionTitle>

      <GlassCard style={{ padding: "20px 22px", marginBottom: 14 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
          <div style={{ width: 34, height: 34, borderRadius: 10, background: U.cyanSoft, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Server size={16} color={U.cyan} />
          </div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 700, color: U.text }}>API Connections</div>
            <div style={{ fontSize: 10, color: U.textMute }}>Data provider status</div>
          </div>
        </div>
        {connections.map(c => {
          return (
            <div key={c.name} style={{ display: "flex", alignItems: "center", gap: 12, padding: "10px 0", borderBottom: `1px solid ${U.border}` }}>
              {c.ok ? <CheckCircle size={16} color={U.emerald} /> : <XCircle size={16} color={U.rose} />}
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: U.text }}>{c.name}</div>
                <div style={{ fontSize: 10, color: U.textMute }}>{c.label}</div>
              </div>
              <span style={{ fontSize: 10, fontWeight: 600, color: c.ok ? U.emerald : U.rose, background: c.ok ? U.emeraldSoft : U.roseSoft, padding: "3px 10px", borderRadius: 999 }}>{c.ok ? 'Connected' : 'Not set'}</span>
            </div>
          );
        })}
      </GlassCard>

      <GlassCard style={{ padding: "20px 22px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
          <div style={{ width: 34, height: 34, borderRadius: 10, background: U.violetSoft, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Palette size={16} color={U.violet} />
          </div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 700, color: U.text }}>Appearance</div>
            <div style={{ fontSize: 10, color: U.textMute }}>Display preferences</div>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "10px 0" }}>
          <div>
            <div style={{ fontSize: 12, fontWeight: 600, color: U.text }}>Theme</div>
            <div style={{ fontSize: 10, color: U.textMute }}>Dark mode (default)</div>
          </div>
          <div style={{
            width: 44, height: 24, borderRadius: 999, background: U.glassHi, border: `1px solid ${U.border}`,
            display: "flex", alignItems: "center", padding: "0 4px", cursor: "not-allowed", opacity: 0.6
          }}>
            <div style={{ width: 16, height: 16, borderRadius: "50%", background: U.cyan, marginLeft: "auto" }} />
          </div>
        </div>
        <div style={{ fontSize: 10, color: U.textFaint, marginTop: 8 }}>Theme customization coming soon.</div>
      </GlassCard>
    </div>
  );
}
