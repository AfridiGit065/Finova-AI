import { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate, Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, TrendingUp, Bot, BarChart2, Globe } from 'lucide-react';
import { AmbientBg } from '@/components/layout/ambient-bg';
import { TickerTape } from '@/components/layout/ticker-tape';
import { Sidebar } from '@/components/layout/sidebar';
import { Header } from '@/components/layout/header';
import { ToastProvider } from '@/components/shared/toast-provider';
import { ThemeProvider } from '@/components/shared/theme-provider';
import { NotificationProvider } from '@/components/shared/notification-provider';
import { U } from '@/lib/constants';
import { useResponsive } from '@/hooks/use-responsive';
import { SupportChat } from '@/components/shared/support-chat';

import DashboardPage from '@/pages/DashboardPage';
import TechnicalPage from '@/pages/TechnicalPage';
import CopilotPage from '@/pages/CopilotPage';
import ComparePage from '@/pages/ComparePage';
import NewsPage from '@/pages/NewsPage';
import SettingsPage from '@/pages/SettingsPage';
import NotificationsPage from '@/pages/NotificationsPage';
import SearchPage from '@/pages/SearchPage';

const MOBILE_NAV = [
  { id: "dashboard", label: "Overview", icon: LayoutDashboard, href: "/dashboard" },
  { id: "technical", label: "Technical", icon: TrendingUp, href: "/technical" },
  { id: "copilot", label: "Copilot", icon: Bot, href: "/copilot" },
  { id: "compare", label: "Compare", icon: BarChart2, href: "/compare" },
  { id: "news", label: "News", icon: Globe, href: "/news" },
];

function AppContent() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const location = useLocation();
  const pathname = location.pathname;
  const isCopilot = pathname === '/copilot';
  const { isMobile } = useResponsive();

  return (
    <div style={{ display: "flex", height: "100vh", position: "relative", zIndex: 1, overflow: "hidden" }}>
      <Sidebar open={sidebarOpen} mobile={isMobile} onClose={() => setSidebarOpen(false)} />
      
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden", minWidth: 0 }}>
        <TickerTape />
        <Header sidebarOpen={sidebarOpen} setSidebarOpen={setSidebarOpen} />

        <main style={{ 
          flex: 1, 
          overflowY: isCopilot ? "hidden" : "auto", 
          padding: isCopilot ? 0 : "var(--main-p)" as any, 
          background: "var(--glass-lo)",
          position: "relative",
          paddingBottom: isCopilot ? 0 : "calc(var(--main-p) + var(--bottom-nav-h))" as any,
        }}>
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/technical" element={<TechnicalPage />} />
            <Route path="/copilot" element={<CopilotPage />} />
            <Route path="/compare" element={<ComparePage />} />
            <Route path="/news" element={<NewsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/notifications" element={<NotificationsPage />} />
            <Route path="/search" element={<SearchPage />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </main>
      </div>

      {isMobile && (
        <div style={{
          position: "fixed", bottom: 0, left: 0, right: 0, height: "var(--bottom-nav-h)" as any,
          background: U.navBg, backdropFilter: "blur(30px) saturate(160%)",
          WebkitBackdropFilter: "blur(30px) saturate(160%)",
          borderTop: `1px solid ${U.border}`,
          display: "flex", alignItems: "center", justifyContent: "space-around",
          zIndex: 100,
        }}>
          {MOBILE_NAV.map(({ id, label, icon: Icon, href }) => {
            const act = pathname === href || (pathname === '/' && id === 'dashboard');
            return (
              <Link key={id} to={href} style={{ textDecoration: 'none', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2, padding: '6px 0', flex: 1 }}>
                <Icon size={18} color={act ? U.cyan : U.textMute} />
                <span style={{ fontSize: 9, fontWeight: act ? 700 : 500, color: act ? U.cyan : U.textMute }}>{label}</span>
              </Link>
            );
          })}
        </div>
      )}
      {!isCopilot && <SupportChat />}
    </div>
  );
}

function App() {
  return (
    <ThemeProvider>
      <AmbientBg />
      <ToastProvider>
        <NotificationProvider>
          <BrowserRouter>
            <AppContent />
          </BrowserRouter>
        </NotificationProvider>
      </ToastProvider>
    </ThemeProvider>
  );
}

export default App;
