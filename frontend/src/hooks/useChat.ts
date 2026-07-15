import { useEffect, useCallback, useRef } from 'react';
import { useChatStore } from '@/stores/chatStore';
import { ws } from '@/utils/websocket';

export function useChat() {
  const store = useChatStore();
  const initialized = useRef(false);

  useEffect(() => {
    if (!initialized.current) {
      initialized.current = true;
      store.loadConversations();
    }
  }, []);

  useEffect(() => {
    const unsubChunk = ws.on('stream_chunk', (data: unknown) => {
      const d = data as { content: string };
      store.appendStreamChunk(d.content);
    });

    const unsubEnd = ws.on('stream_end', () => {
      store.finishStream();
    });

    const unsubMsg = ws.on('message', (msg: unknown) => {
      store.addMessage(msg as Parameters<typeof store.addMessage>[0]);
    });

    return () => {
      unsubChunk();
      unsubEnd();
      unsubMsg();
    };
  }, []);

  const send = useCallback(
    async (content: string) => {
      await store.sendMessage(content);
    },
    [store.sendMessage],
  );

  return {
    conversations: store.conversations,
    messages: store.messages,
    activeConversationId: store.activeConversationId,
    isStreaming: store.isStreaming,
    streamingContent: store.streamingContent,
    isLoadingConversations: store.isLoadingConversations,
    isLoadingMessages: store.isLoadingMessages,
    sendMessage: send,
    setActiveConversation: store.setActiveConversation,
    createConversation: store.createConversation,
    deleteConversation: store.deleteConversation,
  };
}
