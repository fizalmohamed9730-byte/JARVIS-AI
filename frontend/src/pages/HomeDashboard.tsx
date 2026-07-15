import { MessageSquare, CheckSquare, StickyNote, Calendar, Mail, Brain, Zap } from 'lucide-react';
import { Link } from 'react-router-dom';

const features = [
  { icon: MessageSquare, label: 'AI Chat', desc: 'Talk to JARVIS', to: '/chat' },
  { icon: CheckSquare, label: 'Tasks', desc: 'Manage your tasks', to: '/tasks' },
  { icon: StickyNote, label: 'Notes', desc: 'Capture your thoughts', to: '/notes' },
  { icon: Calendar, label: 'Calendar', desc: 'Your schedule', to: '/calendar' },
  { icon: Mail, label: 'Email', desc: 'Read & compose emails', to: '/email' },
  { icon: Brain, label: 'Memory', desc: 'Long-term knowledge', to: '/memory' },
  { icon: Zap, label: 'Automation', desc: 'Automate workflows', to: '/automation' },
];

export default function HomeDashboard() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[80vh] p-8">
      <h1 className="text-4xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
        JARVIS
      </h1>
      <p className="text-slate-400 mb-10 text-lg">Your AI Personal Assistant</p>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 max-w-3xl">
        {features.map(({ icon: Icon, label, desc, to }) => (
          <Link
            key={to}
            to={to}
            className="flex flex-col items-center gap-2 p-5 rounded-2xl bg-slate-800/50 border border-slate-700/50 hover:bg-slate-800 hover:border-slate-600 transition-all duration-200"
          >
            <Icon className="w-8 h-8 text-blue-400" />
            <span className="font-medium text-sm">{label}</span>
            <span className="text-xs text-slate-500 text-center">{desc}</span>
          </Link>
        ))}
      </div>
    </div>
  );
}
