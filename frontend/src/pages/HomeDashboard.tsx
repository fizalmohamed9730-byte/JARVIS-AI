import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  MessageSquare, CheckSquare, StickyNote, Calendar, Mail, Brain, Zap,
  FolderOpen, Activity, CloudSun, Newspaper, Bell, Bot, Image, Video,
  UserCircle, Monitor, Loader2,
} from 'lucide-react';
import { format } from 'date-fns';
import { api } from '@/utils/api';

interface FeatureCard {
  icon: React.ElementType;
  label: string;
  to: string;
  color: string;
}

const features: FeatureCard[] = [
  { icon: UserCircle, label: 'AI Avatar', to: '/chat', color: '#6366f1' },
  { icon: Calendar, label: 'Calendar', to: '/calendar', color: '#3b82f6' },
  { icon: Mail, label: 'Emails', to: '/email', color: '#ef4444' },
  { icon: MessageSquare, label: 'Recent Chat', to: '/chat', color: '#8b5cf6' },
  { icon: CheckSquare, label: 'Tasks', to: '/tasks', color: '#10b981' },
  { icon: Brain, label: 'Memory', to: '/memory', color: '#f59e0b' },
  { icon: FolderOpen, label: 'Recent Files', to: '/files', color: '#f97316' },
  { icon: Zap, label: 'Automation', to: '/automation', color: '#06b6d4' },
  { icon: Monitor, label: 'System Monitor', to: '/automation', color: '#22c55e' },
  { icon: CloudSun, label: 'Weather', to: '/', color: '#0ea5e9' },
  { icon: Newspaper, label: 'News', to: '/', color: '#a855f7' },
  { icon: Bell, label: 'Notifications', to: '/settings', color: '#ec4899' },
  { icon: Bot, label: 'AI Models', to: '/settings', color: '#14b8a6' },
  { icon: Image, label: 'Image Studio', to: '/images', color: '#f43f5e' },
  { icon: Video, label: 'Video Studio', to: '/video', color: '#8b5cf6' },
];

const today = new Date();
const greeting = (() => {
  const h = today.getHours();
  if (h < 12) return 'Good Morning';
  if (h < 17) return 'Good Afternoon';
  return 'Good Evening';
})();

export default function HomeDashboard() {
  const [weather, setWeather] = useState<{
    temperature: number | null;
    condition: string | null;
    location: string;
    humidity: number | null;
    wind_speed: number | null;
  } | null>(null);
  const [weatherLoading, setWeatherLoading] = useState(true);

  useEffect(() => {
    api.get('/weather').then((res) => {
      if (res.data && res.data.temperature != null) {
        setWeather(res.data);
      }
    }).catch(() => {}).finally(() => setWeatherLoading(false));
  }, []);

  return (
    <div className="mx-auto max-w-4xl space-y-6 p-6 pt-8">
      {/* Header */}
      <div
        className="rounded-2xl p-6"
        style={{
          background: 'var(--bg-elevated)',
          border: '1px solid var(--border)',
        }}
      >
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
              {greeting}
            </h1>
            <p className="mt-1 text-sm" style={{ color: 'var(--text-muted)' }}>
              {format(today, 'EEEE, d MMMM yyyy')}
            </p>
          </div>
          {weatherLoading ? (
            <div className="flex items-center gap-2 rounded-xl px-4 py-2" style={{ background: 'var(--glass-bg)', border: '1px solid var(--border)' }}>
              <Loader2 className="h-5 w-5 animate-spin" style={{ color: 'var(--text-muted)' }} />
            </div>
          ) : weather ? (
            <div className="flex items-center gap-2 rounded-xl px-4 py-2" style={{ background: 'var(--glass-bg)', border: '1px solid var(--border)' }}>
              <CloudSun className="h-5 w-5" style={{ color: '#f59e0b' }} />
              <span className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>{Math.round(weather.temperature!)}°C</span>
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{weather.condition} &middot; {weather.location}</span>
            </div>
          ) : null}
        </div>
      </div>

      {/* Feature Grid */}
      <div className="grid grid-cols-3 gap-3">
        {features.map(({ icon: Icon, label, to, color }) => (
          <Link
            key={label}
            to={to}
            className="group flex flex-col items-center justify-center gap-2 rounded-2xl p-5 transition-all duration-200 hover:-translate-y-0.5"
            style={{
              background: 'var(--glass-bg)',
              border: '1px solid var(--border)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'var(--glass-hover)';
              e.currentTarget.style.borderColor = `${color}40`;
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'var(--glass-bg)';
              e.currentTarget.style.borderColor = 'var(--border)';
            }}
          >
            <div
              className="flex items-center justify-center rounded-xl p-3 transition-transform group-hover:scale-110"
              style={{ background: `${color}15` }}
            >
              <Icon className="h-6 w-6" style={{ color }} />
            </div>
            <span className="text-sm font-medium text-center" style={{ color: 'var(--text-primary)' }}>
              {label}
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}
