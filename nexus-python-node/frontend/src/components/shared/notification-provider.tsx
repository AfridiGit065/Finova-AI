'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { useToast } from './toast-provider';
import { useLiveTickers } from '@/hooks/use-live-tickers';

export interface PriceAlert {
  id: string;
  symbol: string;
  type: 'above' | 'below';
  value: number;
  createdAt: string;
  active: boolean;
}

export interface MarketNotification {
  id: string;
  title: string;
  message: string;
  timestamp: string;
  read: boolean;
  symbol: string;
  type: 'price' | 'news' | 'signal';
}

interface NotificationContextValue {
  alerts: PriceAlert[];
  notifications: MarketNotification[];
  createAlert: (symbol: string, type: 'above' | 'below', value: number) => void;
  deleteAlert: (id: string) => void;
  markAsRead: (id: string) => void;
  markAllAsRead: () => void;
  deleteNotification: (id: string) => void;
  clearAllNotifications: () => void;
  unreadCount: number;
}

const NotificationContext = createContext<NotificationContextValue | null>(null);

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const [alerts, setAlerts] = useState<PriceAlert[]>([]);
  const [notifications, setNotifications] = useState<MarketNotification[]>([]);
  const { toast } = useToast();
  const live = useLiveTickers();
  const prevLive = useRef<Record<string, number>>({});

  // 1. Initial Load from localStorage (deferred to bypass SSR mismatch and effect warnings)
  useEffect(() => {
    let active = true;
    Promise.resolve().then(() => {
      if (!active) return;
      try {
        const storedAlerts = localStorage.getItem('nexus-alerts');
        if (storedAlerts) setAlerts(JSON.parse(storedAlerts));

        const storedNotifications = localStorage.getItem('nexus-notifications');
        if (storedNotifications) setNotifications(JSON.parse(storedNotifications));
      } catch {}
    });
    return () => { active = false; };
  }, []);

  // 2. Sync helper functions
  const saveAlerts = (newAlerts: PriceAlert[]) => {
    setAlerts(newAlerts);
    try {
      localStorage.setItem('nexus-alerts', JSON.stringify(newAlerts));
    } catch {}
  };

  const saveNotifications = (newNotifications: MarketNotification[]) => {
    setNotifications(newNotifications);
    try {
      localStorage.setItem('nexus-notifications', JSON.stringify(newNotifications));
    } catch {}
  };

  // 3. Dynamic Alert checking logic
  useEffect(() => {
    if (!alerts.length || !Object.keys(live).length) return;

    const updatedAlerts = alerts.map(a => ({ ...a }));
    let triggeredAny = false;
    const triggeredNotifications: MarketNotification[] = [];

    for (const alert of updatedAlerts) {
      if (!alert.active) continue;

      const liveData = live[alert.symbol];
      if (!liveData || liveData.price === 0) continue;

      const curPrice = liveData.price;
      let isTriggered = false;

      if (alert.type === 'above' && curPrice >= alert.value) {
        isTriggered = true;
      } else if (alert.type === 'below' && curPrice <= alert.value) {
        isTriggered = true;
      }

      if (isTriggered) {
        alert.active = false; // Prevent repeated triggering
        triggeredAny = true;

        const notif: MarketNotification = {
          id: Math.random().toString(36).substring(2, 9),
          title: `Alert Triggered: ${alert.symbol}`,
          message: `${alert.symbol} is currently $${curPrice.toFixed(2)}, which has crossed your target threshold of $${alert.value.toFixed(2)}.`,
          timestamp: new Date().toISOString(),
          read: false,
          symbol: alert.symbol,
          type: 'price',
        };

        triggeredNotifications.push(notif);
        toast('info', `${alert.symbol} hit target of $${alert.value.toFixed(2)} (Current: $${curPrice.toFixed(2)})`);
      }
    }

    if (triggeredAny) {
      Promise.resolve().then(() => {
        saveAlerts(updatedAlerts);
        saveNotifications([...triggeredNotifications, ...notifications]);
      });
    }

    // Capture current prices for comparison
    for (const key of Object.keys(live)) {
      if (live[key].price > 0) {
        prevLive.current[key] = live[key].price;
      }
    }
  }, [live, alerts, notifications, toast]);

  const createAlert = useCallback((symbol: string, type: 'above' | 'below', value: number) => {
    const newAlert: PriceAlert = {
      id: Math.random().toString(36).substring(2, 9),
      symbol,
      type,
      value,
      createdAt: new Date().toISOString(),
      active: true,
    };
    setAlerts(prev => {
      const next = [newAlert, ...prev];
      try {
        localStorage.setItem('nexus-alerts', JSON.stringify(next));
      } catch {}
      return next;
    });
    toast('success', `Price alert created for ${symbol} at $${value.toFixed(2)}`);
  }, [toast]);

  const deleteAlert = useCallback((id: string) => {
    setAlerts(prev => {
      const next = prev.filter(a => a.id !== id);
      try {
        localStorage.setItem('nexus-alerts', JSON.stringify(next));
      } catch {}
      return next;
    });
  }, []);

  const markAsRead = useCallback((id: string) => {
    setNotifications(prev => {
      const next = prev.map(n => n.id === id ? { ...n, read: true } : n);
      try {
        localStorage.setItem('nexus-notifications', JSON.stringify(next));
      } catch {}
      return next;
    });
  }, []);

  const markAllAsRead = useCallback(() => {
    setNotifications(prev => {
      const next = prev.map(n => ({ ...n, read: true }));
      try {
        localStorage.setItem('nexus-notifications', JSON.stringify(next));
      } catch {}
      return next;
    });
  }, []);

  const deleteNotification = useCallback((id: string) => {
    setNotifications(prev => {
      const next = prev.filter(n => n.id !== id);
      try {
        localStorage.setItem('nexus-notifications', JSON.stringify(next));
      } catch {}
      return next;
    });
  }, []);

  const clearAllNotifications = useCallback(() => {
    setNotifications([]);
    try {
      localStorage.setItem('nexus-notifications', JSON.stringify([]));
    } catch {}
  }, []);

  const unreadCount = notifications.filter(n => !n.read).length;

  return (
    <NotificationContext.Provider value={{
      alerts,
      notifications,
      createAlert,
      deleteAlert,
      markAsRead,
      markAllAsRead,
      deleteNotification,
      clearAllNotifications,
      unreadCount
    }}>
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotifications() {
  const ctx = useContext(NotificationContext);
  if (!ctx) throw new Error('useNotifications must be used within NotificationProvider');
  return ctx;
}
