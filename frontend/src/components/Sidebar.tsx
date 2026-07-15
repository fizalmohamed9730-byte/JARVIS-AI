import { useLocation, useNavigate } from 'react-router-dom';
import {
  MessageSquare,
  CheckSquare,
  StickyNote,
  Calendar,
  Mail,
  Settings,
  Zap,
  Brain,
  PanelLeftClose,
  PanelLeft,
  Folder,
  Image as ImageIcon,
  Globe,
  Film,
} from 'lucide-react';
import clsx from 'clsx';
import ConversationHistory from './ConversationHistory';

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

const navItems = [
  { path: '/', icon: MessageSquare, label: 'Chat' },
  { path: '/tasks', icon: CheckSquare, label: 'Tasks' },
  { path: '/notes', icon: StickyNote, label: 'Notes' },
  { path: '/calendar', icon: Calendar, label: 'Calendar' },
  { path: '/email', icon: Mail, label: 'Email' },
  { path: '/memory', icon: Brain, label: 'Memory' },
  { path: '/automation', icon: Zap, label: 'Automation' },
  { path: '/files', icon: Folder, label: 'Files' },
  { path: '/images', icon: ImageIcon, label: 'Images' },
  { path: '/websites', icon: Globe, label: 'Websites' },
  { path: '/video', icon: Film, label: 'Video' },
];

export default function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const location = useLocation();
  const navigate = useNavigate();

  return (
    <aside
      className={clsx(
        'flex h-full flex-col border-r border-white/10 bg-slate-950/70 backdrop-blur-xl transition-all duration-300',
        collapsed ? 'w-16' : 'w-64',
      )}
    >
      {/* Logo */}
      <div className="flex h-14 items-center justify-between border-b border-white/10 px-4">
        {!collapsed && (
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-500/20 animate-pulse-glow">
              <span className="text-sm font-bold text-blue-400 glow-text">J</span>
            </div>
            <span className="text-sm font-semibold tracking-wider text-white">JARVIS</span>
          </div>
        )}
        <button
          onClick={onToggle}
          className="rounded-md p-1.5 text-gray-400 transition-colors hover:bg-white/10 hover:text-white"
        >
          {collapsed ? <PanelLeft className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-2 py-3">
        <div className="space-y-1">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <button
                key={item.path}
                onClick={() => navigate(item.path)}
                className={clsx(
                  'flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all',
                  isActive
                    ? 'bg-blue-500/15 text-blue-400 glow-border'
                    : 'text-gray-400 hover:bg-white/5 hover:text-gray-200',
                  collapsed && 'justify-center px-0',
                )}
              >
                <item.icon className="h-5 w-5 flex-shrink-0" />
                {!collapsed && <span>{item.label}</span>}
              </button>
            );
          })}
        </div>

        {location.pathname === '/' && !collapsed && (
          <div className="mt-4">
            <ConversationHistory />
          </div>
        )}
      </nav>

      {/* Settings + User */}
      <div className="border-t border-white/10 p-3">
        <button
          onClick={() => navigate('/settings')}
          className={clsx(
            'flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-gray-400 transition-all hover:bg-white/5 hover:text-gray-200',
            location.pathname === '/settings' && 'bg-white/5 text-white',
            collapsed && 'justify-center px-0',
          )}
        >
          <Settings className="h-5 w-5" />
          {!collapsed && <span>Settings</span>}
        </button>
        {!collapsed && (
          <div className="mt-3 flex items-center gap-3 rounded-lg bg-white/5 px-3 py-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-blue-700 text-xs font-bold">
              J
            </div>
            <div className="flex-1 truncate">
              <p className="text-sm font-medium text-white">User</p>
              <p className="text-xs text-gray-500">user@jarvis.ai</p>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
