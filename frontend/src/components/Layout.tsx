import { ReactNode, useState } from 'react';
import Sidebar from './Sidebar';
import { Mic, Search, Bell } from 'lucide-react';
import { useVoice } from '@/hooks/useVoice';

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <div className="flex h-screen w-screen overflow-hidden jarvis-gradient">
      <Sidebar collapsed={sidebarCollapsed} onToggle={() => setSidebarCollapsed(!sidebarCollapsed)} />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-4 lg:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}

function Header() {
  const { isListening, startListening, stopListening } = useVoice();

  return (
    <header className="flex h-14 items-center justify-between border-b border-white/10 bg-slate-950/50 px-4 backdrop-blur-md drag">
      <div className="flex items-center gap-2 no-drag">
        <div className="relative">
          <Search className="absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Search JARVIS..."
            className="ml-2 w-64 rounded-lg border border-white/10 bg-white/5 py-1.5 pl-8 pr-3 text-sm text-gray-200 placeholder-gray-500 outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/30"
          />
        </div>
      </div>
      <div className="flex items-center gap-3 no-drag">
        <button
          onClick={isListening ? stopListening : startListening}
          className={`relative rounded-full p-2 transition-all ${
            isListening
              ? 'bg-blue-500/20 text-blue-400 animate-pulse-glow'
              : 'bg-white/5 text-gray-400 hover:bg-white/10 hover:text-white'
          }`}
        >
          <Mic className="h-4 w-4" />
        </button>
        <button className="relative rounded-full bg-white/5 p-2 text-gray-400 transition-all hover:bg-white/10 hover:text-white">
          <Bell className="h-4 w-4" />
          <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-blue-500" />
        </button>
        <div className="ml-2 flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-blue-700 text-xs font-semibold text-white">
          J
        </div>
      </div>
    </header>
  );
}
