'use client';

import React, { createContext, useContext, useEffect, useState, useCallback, useMemo } from 'react';

export type ThemeMode = 'light' | 'dark' | 'system';
export type ResolvedTheme = 'light' | 'dark';

export interface ChartThemeColors {
  grid: string;
  text: string;
  textMuted: string;
  tooltipBg: string;
  tooltipBorder: string;
  tooltipText: string;
  primary: string;
  accent: string;
  success: string;
  warning: string;
  error: string;
  cardBg: string;
  cyan: string;
  purple: string;
  emerald: string;
  amber: string;
  rose: string;
}

interface ThemeContextType {
  theme: ThemeMode;
  resolvedTheme: ResolvedTheme;
  setTheme: (theme: ThemeMode) => void;
  toggleTheme: () => void;
  isMounted: boolean;
  chartColors: ChartThemeColors;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

const STORAGE_KEY = 'quizverse_theme';

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = useState<ThemeMode>('dark');
  const [resolvedTheme, setResolvedTheme] = useState<ResolvedTheme>('dark');
  const [isMounted, setIsMounted] = useState<boolean>(false);

  // Derive system color scheme preference
  const getSystemTheme = useCallback((): ResolvedTheme => {
    if (typeof window === 'undefined') return 'dark';
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }, []);

  // Update DOM classes (.light or .dark on documentElement)
  const applyThemeToDOM = useCallback((resolved: ResolvedTheme) => {
    if (typeof document === 'undefined') return;
    const root = document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(resolved);
    root.setAttribute('data-theme', resolved);
    root.style.colorScheme = resolved;
  }, []);

  // Initialize theme from storage on mount
  useEffect(() => {
    setIsMounted(true);

    try {
      const stored = localStorage.getItem(STORAGE_KEY) as ThemeMode | null;
      const initialTheme: ThemeMode = stored === 'light' || stored === 'dark' || stored === 'system' ? stored : 'dark';
      setThemeState(initialTheme);

      const effective: ResolvedTheme = initialTheme === 'system' ? getSystemTheme() : initialTheme;
      setResolvedTheme(effective);
      applyThemeToDOM(effective);
    } catch {
      // Fallback if localStorage is inaccessible
      applyThemeToDOM('dark');
    }
  }, [getSystemTheme, applyThemeToDOM]);

  // Listen to OS system color scheme changes when in 'system' mode
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

    const handleChange = (e: MediaQueryListEvent) => {
      if (theme === 'system') {
        const newResolved: ResolvedTheme = e.matches ? 'dark' : 'light';
        setResolvedTheme(newResolved);
        applyThemeToDOM(newResolved);
      }
    };

    mediaQuery.addEventListener('change', handleChange);
    return () => mediaQuery.removeEventListener('change', handleChange);
  }, [theme, applyThemeToDOM]);

  // Set theme handler with persistence
  const setTheme = useCallback(
    (newTheme: ThemeMode) => {
      setThemeState(newTheme);
      try {
        localStorage.setItem(STORAGE_KEY, newTheme);
      } catch {
        // Safe fallback
      }

      const effective: ResolvedTheme = newTheme === 'system' ? getSystemTheme() : newTheme;
      setResolvedTheme(effective);
      applyThemeToDOM(effective);
    },
    [getSystemTheme, applyThemeToDOM]
  );

  // Quick toggle between Light and Dark
  const toggleTheme = useCallback(() => {
    const nextTheme: ThemeMode = resolvedTheme === 'dark' ? 'light' : 'dark';
    setTheme(nextTheme);
  }, [resolvedTheme, setTheme]);

  // Theme-aware Chart Palette tokens
  const chartColors: ChartThemeColors = useMemo(() => {
    if (resolvedTheme === 'light') {
      return {
        grid: '#E4E7EC',
        text: '#475467',
        textMuted: '#98A2B3',
        tooltipBg: '#FFFFFF',
        tooltipBorder: '#D0D5DD',
        tooltipText: '#182230',
        primary: '#6257E8',
        accent: '#06B6D4',
        success: '#159B68',
        warning: '#D99018',
        error: '#D64545',
        cardBg: '#FFFFFF',
        cyan: '#0284C7',
        purple: '#7C3AED',
        emerald: '#159B68',
        amber: '#D99018',
        rose: '#D64545',
      };
    }
    return {
      grid: 'rgba(255, 255, 255, 0.08)',
      text: '#94A3B8',
      textMuted: '#64748B',
      tooltipBg: '#0F172A',
      tooltipBorder: 'rgba(255, 255, 255, 0.12)',
      tooltipText: '#F8FAFC',
      primary: '#4668FA',
      accent: '#00F5D4',
      success: '#10B981',
      warning: '#F59E0B',
      error: '#EF4444',
      cardBg: '#151C30',
      cyan: '#06B6D4',
      purple: '#8B5CF6',
      emerald: '#10B981',
      amber: '#F59E0B',
      rose: '#EF4444',
    };
  }, [resolvedTheme]);

  const value = useMemo(
    () => ({
      theme,
      resolvedTheme,
      setTheme,
      toggleTheme,
      isMounted,
      chartColors,
    }),
    [theme, resolvedTheme, setTheme, toggleTheme, isMounted, chartColors]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}
