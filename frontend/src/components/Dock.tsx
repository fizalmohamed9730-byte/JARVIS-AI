import { NavLink } from 'react-router-dom';
import {
  Home, MessageSquare, CheckSquare, StickyNote, Calendar,
  Mail, Settings, Brain, Zap, FolderOpen, Image, Globe, Video,
} from 'lucide-react';

const items = [
  { icon: Home, to: '/', label: 'Home' },
  { icon: MessageSquare, to: '/chat', label: 'Chat' },
  { icon: CheckSquare, to: '/tasks', label: 'Tasks' },
  { icon: StickyNote, to: '/notes', label: 'Notes' },
  { icon: Calendar, to: '/calendar', label: 'Calendar' },
  { icon: Mail, to: '/email', label: 'Email' },
  { icon: Brain, to: '/memory', label: 'Memory' },
  { icon: Zap, to: '/automation', label: 'Auto' },
  { icon: FolderOpen, to: '/files', label: 'Files' },
  { icon: Image, to: '/images', label: 'Images' },
  { icon: Globe, to: '/websites', label: 'Websites' },
  { icon: Video, to: '/video', label: 'Video' },
  { icon: Settings, to: '/settings', label: 'Settings' },
];

export default function Dock() {
  return (
    <nav className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 flex items-center gap-1 px-3 py-2 rounded-2xl bg-slate-900/80 backdrop-blur-xl border border-slate-700/50 shadow-2xl">
      {items.map(({ icon: Icon, to, label }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          className={({ isActive }) =>
            `flex flex-col items-center gap-0.5 px-2.5 py-1.5 rounded-xl text-xs transition-colors ${
              isActive
                ? 'bg-blue-600/20 text-blue-400'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`
          }
        >
          <Icon className="w-5 h-5" />
          <span className="text-[10px] hidden md:block">{label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
