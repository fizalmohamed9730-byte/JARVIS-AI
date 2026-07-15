import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';

type Theme = 'light' | 'dark' | 'amoled' | 'glass' | 'auto';

interface ThemeContextProps {
  theme: Theme;
  setTheme: (theme: Theme) => void;
}

const ThemeContext = createContext<ThemeContextProps | undefined>(undefined);

export const useTheme = (): ThemeContextProps => {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    throw new Error('useTheme must be used within ThemeProvider');
  }
  return ctx;
};

export const ThemeProvider = ({ children }: { children: ReactNode }) => {
  const [theme, setThemeState] = useState<Theme>('auto');

  // Load persisted preference
  useEffect(() => {
    const stored = localStorage.getItem('jarvis-theme') as Theme | null;
    if (stored) {
      setThemeState(stored);
    }
  }, []);

  // Apply theme class to html element
  useEffect(() => {
    const root = document.documentElement;
    const apply = (t: Theme) => {
      root.classList.remove('theme-light', 'theme-dark', 'theme-amoled', 'theme-glass');
      if (t !== 'auto') {
        root.classList.add(`theme-${t}`);
      }
    };
    if (theme === 'auto') {
      const mq = window.matchMedia('(prefers-color-scheme: dark)');
      const handler = (e: MediaQueryListEvent) => {
        apply(e.matches ? 'dark' : 'light');
      };
      apply(mq.matches ? 'dark' : 'light');
      mq.addEventListener('change', handler);
      return () => mq.removeEventListener('change', handler);
    } else {
      apply(theme);
    }
  }, [theme]);

  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme);
    localStorage.setItem('jarvis-theme', newTheme);
  };

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};
