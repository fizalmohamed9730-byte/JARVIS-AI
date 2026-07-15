import { useChat } from '@/hooks/useChat';
import { MessageSquare, Trash2, Plus } from 'lucide-react';
import { format } from 'date-fns';
import clsx from 'clsx';

export default function ConversationHistory() {
  const { conversations, activeConversationId, setActiveConversation, createConversation, deleteConversation } = useChat();

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between px-1 pb-2">
        <span className="text-[10px] font-medium uppercase tracking-wider text-gray-600">Recent</span>
        <button
          onClick={() => createConversation()}
          className="rounded p-1 text-gray-600 hover:bg-white/10 hover:text-white"
        >
          <Plus className="h-3 w-3" />
        </button>
      </div>
      {conversations.slice(0, 10).map((conv) => (
        <div
          key={conv.id}
          className={clsx(
            'group flex cursor-pointer items-center gap-2 rounded-lg px-2 py-1.5 transition-all',
            activeConversationId === conv.id ? 'bg-blue-500/10 text-blue-400' : 'text-gray-500 hover:bg-white/5 hover:text-gray-300',
          )}
          onClick={() => setActiveConversation(conv.id)}
        >
          <MessageSquare className="h-3.5 w-3.5 flex-shrink-0" />
          <span className="flex-1 truncate text-xs">{conv.title}</span>
          <button
            onClick={(e) => {
              e.stopPropagation();
              deleteConversation(conv.id);
            }}
            className="rounded p-0.5 text-gray-700 opacity-0 transition-all hover:text-red-400 group-hover:opacity-100"
          >
            <Trash2 className="h-3 w-3" />
          </button>
        </div>
      ))}
      {conversations.length === 0 && (
        <p className="px-2 py-4 text-center text-[10px] text-gray-600">No conversations yet</p>
      )}
    </div>
  );
}
