import { useEffect, useRef } from 'react';
import { useChat } from '@/hooks/useChat';
import MessageBubble from './MessageBubble';
import ChatInput from './ChatInput';
import TypingIndicator from './TypingIndicator';
import EmptyState from './EmptyState';

export default function ChatInterface() {
  const { messages, isStreaming, streamingContent, sendMessage, isLoadingMessages } = useChat();
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  return (
    <div className="flex h-full flex-col">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 pb-4">
        {isLoadingMessages ? (
          <div className="flex h-full items-center justify-center">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
          </div>
        ) : messages.length === 0 && !isStreaming ? (
          <EmptyState
            icon="MessageSquare"
            title="Start a conversation"
            description="Ask JARVIS anything — manage tasks, compose emails, check your calendar, or just chat."
          />
        ) : (
          <div className="mx-auto max-w-3xl space-y-4 py-4">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            {isStreaming && streamingContent && (
              <MessageBubble
                message={{
                  id: 'streaming',
                  conversationId: '',
                  role: 'assistant',
                  content: streamingContent,
                  timestamp: new Date().toISOString(),
                  isStreaming: true,
                }}
              />
            )}
            {isStreaming && !streamingContent && <TypingIndicator />}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t p-4 backdrop-blur-md" style={{ borderColor: 'var(--border)', background: 'var(--bg-surface)' }}>
        <div className="mx-auto max-w-3xl">
          <ChatInput onSend={sendMessage} disabled={isStreaming} />
        </div>
      </div>
    </div>
  );
}
