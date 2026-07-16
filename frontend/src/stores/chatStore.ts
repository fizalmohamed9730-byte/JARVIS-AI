import { create } from 'zustand';
import type { Conversation, Message } from '@/types';
import { api } from '@/utils/api';

interface ChatState {
  conversations: Conversation[];
  activeConversationId: string | null;
  messages: Message[];
  isStreaming: boolean;
  streamingContent: string;
  isLoadingConversations: boolean;
  isLoadingMessages: boolean;

  setActiveConversation: (id: string | null) => void;
  loadConversations: () => Promise<void>;
  loadMessages: (conversationId: string) => Promise<void>;
  createConversation: () => Promise<string>;
  deleteConversation: (id: string) => Promise<void>;
  sendMessage: (content: string) => Promise<void>;
  appendStreamChunk: (chunk: string) => void;
  finishStream: () => void;
  addMessage: (message: Message) => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  conversations: [],
  activeConversationId: null,
  messages: [],
  isStreaming: false,
  streamingContent: '',
  isLoadingConversations: false,
  isLoadingMessages: false,

  setActiveConversation: (id) => {
    set({ activeConversationId: id });
    if (id) {
      get().loadMessages(id);
    } else {
      set({ messages: [] });
    }
  },

  loadConversations: async () => {
    set({ isLoadingConversations: true });
    try {
      const res = await api.get('/conversations');
      const list = res.data?.items || res.data || [];
      set({ conversations: list.map((c: Record<string, unknown>) => ({
        id: String(c.id),
        title: c.title as string,
        lastMessage: '',
        lastMessageAt: c.updated_at as string,
        messageCount: 0,
        createdAt: c.created_at as string,
        updatedAt: c.updated_at as string,
      })) });
    } catch {
      set({ conversations: [] });
    } finally {
      set({ isLoadingConversations: false });
    }
  },

  loadMessages: async (conversationId) => {
    set({ isLoadingMessages: true });
    try {
      const res = await api.get(`/conversations/${conversationId}/messages`);
      const list = res.data?.items || res.data || [];
      set({ messages: list.map((m: Record<string, unknown>) => ({
        id: String(m.id),
        conversationId: String(m.conversation_id),
        role: m.role as 'user' | 'assistant' | 'system',
        content: m.content as string,
        timestamp: m.created_at as string,
      })) });
    } catch {
      set({ messages: [] });
    } finally {
      set({ isLoadingMessages: false });
    }
  },

  createConversation: async () => {
    const res = await api.post('/conversations', { title: 'New Chat' });
    const conv = { id: String(res.data.id), title: res.data.title, lastMessage: '', lastMessageAt: res.data.updated_at, messageCount: 0, createdAt: res.data.created_at, updatedAt: res.data.updated_at };
    set((s) => ({ conversations: [conv, ...s.conversations], activeConversationId: conv.id }));
    return conv.id;
  },

  deleteConversation: async (id) => {
    await api.delete(`/conversations/${id}`);
    set((s) => ({
      conversations: s.conversations.filter((c) => c.id !== id),
      activeConversationId: s.activeConversationId === id ? null : s.activeConversationId,
    }));
  },

  sendMessage: async (content) => {
    const { activeConversationId, messages } = get();
    let convId = activeConversationId;

    try {
      if (!convId) {
        convId = await get().createConversation();
      }

      const userMessage: Message = {
        id: crypto.randomUUID(),
        conversationId: convId,
        role: 'user',
        content,
        timestamp: new Date().toISOString(),
      };

      set({ messages: [...messages, userMessage], isStreaming: true, streamingContent: '' });

      await api.post(`/conversations/${convId}/messages`, { role: 'user', content });
    } catch {
      set({ isStreaming: false });
    }
  },

  appendStreamChunk: (chunk) => {
    set((s) => ({ streamingContent: s.streamingContent + chunk }));
  },

  finishStream: () => {
    const { streamingContent, activeConversationId, messages } = get();
    if (streamingContent) {
      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        conversationId: activeConversationId!,
        role: 'assistant',
        content: streamingContent,
        timestamp: new Date().toISOString(),
      };
      set({ messages: [...messages, assistantMessage], isStreaming: false, streamingContent: '' });
    } else {
      set({ isStreaming: false });
    }
  },

  addMessage: (message) => {
    set((s) => ({ messages: [...s.messages, message] }));
  },
}));
