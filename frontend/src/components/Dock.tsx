import { NavLink, useLocation } from 'react-router-dom';
import {
  Home, MessageSquare, Mic, Zap, Brain, Calendar, Mail,
  FolderOpen, Image, Globe, Video, Settings, Cpu,
  PresentationIcon,
} from 'lucide-react';
import { useState } from 'react';

interface DockItem {
  icon: React.ElementType;
  to: string;
  label: string;
  color?: string;
}

const DOCK_ITEMS: DockItem[] = [
  { icon: Home, to: '/', label: 'Home', color: '#6366f1' },
  { icon: MessageSquare, to: '/chat', label: 'Chat', color: '#8b5cf6' },
  { icon: Mic, to: '/voice', label: 'Voice', color: '#06b6d4' },
  { icon: Zap, to: '/automation', label: 'Automation', color: '#f59e0b' },
  { icon: Brain, to: '/memory', label: 'Memory', color: '#10b981' },
  { icon: Calendar, to: '/calendar', label: 'Calendar', color: '#3b82f6' },
  { icon: Mail, to: '/email', label: 'Email', color: '#ef4444' },
  { icon: FolderOpen, to: '/files', label: 'Files', color: '#f97316' },
  { icon: Image, to: '/images', label: 'Image Studio', color: '#ec4899' },
  { icon: PresentationIcon, to: '/presentations', label: 'Presentations', color: '#a855f7' },
  { icon: Globe, to: '/websites', label: 'Web Studio', color: '#14b8a6' },
  { icon: Video, to: '/video', label: 'Video Studio', color: '#f43f5e' },
  { icon: Cpu, to: '/ai-models', label: 'AI Models', color: '#22c55e' },
  { icon: Settings, to: '/settings', label: 'Settings', color: '#64748b' },
];

export default function Dock() {
  const location = useLocation();
  const [hoveredItem, setHoveredItem] = useState<string | null>(null);

  return (
    <nav className="dock no-drag" role="navigation" aria-label="Main navigation">
      {DOCK_ITEMS.map(({ icon: Icon, to, label, color }) => {
        const isActive = to === '/'
          ? location.pathname === '/'
          : location.pathname.startsWith(to);

        return (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={`dock-item ${isActive ? 'active' : ''}`}
            style={isActive ? { '--dock-accent': color } as React.CSSProperties : {}}
            onMouseEnter={() => setHoveredItem(to)}
            onMouseLeave={() => setHoveredItem(null)}
            title={label}
          >
            <Icon
              size={18}
              style={{
                color: isActive ? color : hoveredItem === to ? color : undefined,
                transition: 'color 0.15s ease',
              }}
            />
            <span className="dock-tooltip">{label}</span>
          </NavLink>
        );
      })}
    </nav>
  );
}
