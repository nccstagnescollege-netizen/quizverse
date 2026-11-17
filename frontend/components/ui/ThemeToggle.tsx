'use client';

import { useEffect, useState } from 'react';
import { Sun, Moon } from 'lucide-react';

export function ThemeToggle() {
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');

  useEffect(() => {
    const isLight = document.documentElement.classList.contains('light');
    setTheme(isLight ? 'light' : 'dark');
  }, []);

  const toggleTheme = () => {
    const newTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
    if (newTheme === 'light') {
      document.documentElement.classList.remove('dark');
      document.documentElement.classList.add('light');
    } else {
      document.documentElement.classList.remove('light');
      document.documentElement.classList.add('dark');
    }
  };

  return (
    <button
      onClick={toggleTheme}
      aria-label="Toggle visual theme"
      className="p-2 rounded-xl bg-surface-elevated border border-surface-border text-slate-300 hover:text-white hover:border-brand-500/30 transition-colors focus:outline-none focus:ring-2 focus:ring-brand-500"
    >
      {theme === 'dark' ? <Sun className="w-4 h-4 text-cyber-gold" /> : <Moon className="w-4 h-4 text-brand-600" />}
    </button>
  );
}
