import {
  MessageSquare, CheckSquare, StickyNote, Calendar, Mail,
  Settings, Brain, Zap,
} from 'lucide-react';
import clsx from 'clsx';

const iconMap: Record<string, React.ElementType> = {
  MessageSquare, CheckSquare, StickyNote, Calendar, Mail, Settings, Brain, Zap,
};

interface EmptyStateProps {
  icon?: string;
  title: string;
  description: string;
}

export default function EmptyState({ icon = 'MessageSquare', title, description }: EmptyStateProps) {
  const Icon = iconMap[icon] || MessageSquare;

  return (
    <div className="flex h-full flex-col items-center justify-center py-20 animate-fade-in">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-white/5">
        <Icon className="h-8 w-8 text-gray-600" />
      </div>
      <h3 className="mt-4 text-sm font-medium text-gray-400">{title}</h3>
      <p className="mt-1 max-w-sm text-center text-xs text-gray-600">{description}</p>
    </div>
  );
}
