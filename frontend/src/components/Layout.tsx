import { ReactNode, useState } from 'react';
import { Search, Bell, Sparkles, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useVoice } from '@/hooks/useVoice';
import { useTheme } from '@/theme/ThemeProvider';

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  return (
    <div
      className="flex flex-col w-screen h-screen overflow-hidden"
      style={{ background: 'var(--bg-base)' }}
    >
      <TopBar />
      {/* Main scrollable content area with padding for dock */}
      <main
        className="flex-1 overflow-y-auto overflow-x-hidden"
        style={{ paddingBottom: '100px' }}
      >
        {children}
      </main>
    </div>
  );
}

function TopBar() {
  const { isListening, startListening, stopListening } = useVoice();
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchValue, setSearchValue] = useState('');
  const [notifOpen, setNotifOpen] = useState(false);
  const navigate = useNavigate();
  const { theme, setTheme } = useTheme();

  const themes = ['dark', 'light', 'amoled', 'glass', 'auto'] as const;
  const nextTheme = themes[(themes.indexOf(theme as typeof themes[number]) + 1) % themes.length];

  return (
    <header
      className="no-drag flex items-center justify-between px-6 h-[52px] shrink-0"
      style={{
        background: 'var(--bg-surface)',
        borderBottom: '1px solid var(--border)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        zIndex: 50,
      }}
    >
      {/* Left: Logo + Brand */}
      <div className="flex items-center gap-3 no-drag">
        <div
          className="flex items-center justify-center w-7 h-7 rounded-lg animate-pulse-glow"
          style={{ background: 'linear-gradient(135deg, #6366f1, #8b5cf6)' }}
        >
          <Sparkles size={14} className="text-white" />
        </div>
        <span
          className="font-bold text-sm tracking-widest"
          style={{ color: 'var(--text-primary)', letterSpacing: '0.15em' }}
        >
          JARVIS
        </span>
        <span
          className="badge badge-accent text-[10px]"
          style={{ fontSize: '9px' }}
        >
          3.0
        </span>
      </div>

      {/* Center: Search */}
      <div className="flex-1 max-w-sm mx-6">
        {searchOpen ? (
          <div className="search-bar">
            <Search size={14} style={{ color: 'var(--text-muted)' }} />
            <input
              autoFocus
              type="text"
              placeholder="Search everything..."
              value={searchValue}
              onChange={(e) => setSearchValue(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Escape') {
                  setSearchOpen(false);
                  setSearchValue('');
                }
              }}
            />
            <button
              onClick={() => { setSearchOpen(false); setSearchValue(''); }}
              style={{ color: 'var(--text-muted)' }}
            >
              <X size={14} />
            </button>
          </div>
        ) : (
          <button
            onClick={() => setSearchOpen(true)}
            className="search-bar"
            style={{ cursor: 'text', justifyContent: 'flex-start', width: '100%' }}
          >
            <Search size={14} style={{ color: 'var(--text-muted)' }} />
            <span style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
              Search JARVIS… <kbd style={{ fontSize: '11px', opacity: 0.5 }}>⌘K</kbd>
            </span>
          </button>
        )}
      </div>

      {/* Right: Controls */}
      <div className="flex items-center gap-2 no-drag">
        {/* Voice toggle */}
        <button
          onClick={() => (isListening ? stopListening() : startListening())}
          className="flex items-center justify-center w-8 h-8 rounded-lg transition-all"
          style={{
            background: isListening
              ? 'rgba(239, 68, 68, 0.15)'
              : 'var(--glass-bg)',
            border: `1px solid ${isListening ? 'rgba(239,68,68,0.4)' : 'var(--border)'}`,
            color: isListening ? '#ef4444' : 'var(--text-secondary)',
          }}
          title={isListening ? 'Stop listening' : 'Voice input'}
        >
          {isListening ? (
            <div className="flex gap-[2px] items-center">
              {[0, 1, 2].map(i => (
                <div
                  key={i}
                  className="voice-bar"
                  style={{ height: '12px', animationDelay: `${i * 0.15}s` }}
                />
              ))}
            </div>
          ) : (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
              <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
              <line x1="12" y1="19" x2="12" y2="23"/>
              <line x1="8" y1="23" x2="16" y2="23"/>
            </svg>
          )}
        </button>

        {/* Notifications */}
        <div className="relative">
          <button
            onClick={() => setNotifOpen(p => !p)}
            className="flex items-center justify-center w-8 h-8 rounded-lg transition-all"
            style={{
              background: 'var(--glass-bg)',
              border: '1px solid var(--border)',
              color: 'var(--text-secondary)',
            }}
          >
            <Bell size={14} />
            <span
              className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full"
              style={{ background: '#6366f1' }}
            />
          </button>
          {notifOpen && (
            <div
              className="absolute right-0 top-10 w-80 rounded-2xl overflow-hidden"
              style={{
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border-strong)',
                boxShadow: 'var(--shadow-lg)',
                zIndex: 200,
              }}
            >
              <div className="px-4 py-3 border-b" style={{ borderColor: 'var(--border)' }}>
                <p className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>
                  Notifications
                </p>
              </div>
              {[
                { title: 'JARVIS is ready', desc: 'All systems operational', time: 'now', dot: '#10b981' },
                { title: 'Memory updated', desc: '3 new memories added', time: '2m ago', dot: '#6366f1' },
                { title: 'Task reminder', desc: 'Review project docs due', time: '15m ago', dot: '#f59e0b' },
              ].map((n, i) => (
                <div
                  key={i}
                  className="flex items-start gap-3 px-4 py-3 hover:bg-white/5 cursor-pointer transition-colors"
                >
                  <div
                    className="w-2 h-2 rounded-full mt-1.5 shrink-0"
                    style={{ background: n.dot }}
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                      {n.title}
                    </p>
                    <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{n.desc}</p>
                  </div>
                  <span className="text-xs shrink-0" style={{ color: 'var(--text-muted)' }}>
                    {n.time}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Theme toggle */}
        <button
          onClick={() => setTheme(nextTheme)}
          className="btn-ghost text-xs px-2 py-1"
          title={`Switch to ${nextTheme} theme`}
        >
          {theme === 'dark' ? '🌙' : theme === 'light' ? '☀️' : theme === 'amoled' ? '⚫' : theme === 'glass' ? '🔮' : '🔄'}
        </button>

        {/* Avatar */}
        <button
          onClick={() => navigate('/settings')}
          className="flex items-center justify-center w-8 h-8 rounded-full font-bold text-xs text-white"
          style={{
            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
            boxShadow: '0 2px 10px rgba(99, 102, 241, 0.4)',
          }}
        >
          J
        </button>
      </div>
    </header>
  );
}
