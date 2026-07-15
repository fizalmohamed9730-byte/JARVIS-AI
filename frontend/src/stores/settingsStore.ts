import { create } from 'zustand';
import type { Settings } from '@/types';
import { api } from '@/utils/api';

const defaultSettings: Settings = {
  profile: { name: 'User', email: '' },
  voice: { enabled: true, language: 'en-US', speed: 1.0, wakeWord: 'hey jarvis', continuousMode: false },
  ai: { onlinePreference: 'when-needed', selectedModel: 'gpt-4', temperature: 0.7, maxTokens: 2048 },
  theme: { mode: 'dark', accentColor: '#3b82f6', fontSize: 'md', animations: true },
  notifications: { desktop: true, sound: true, emailDigest: false },
  apiKeys: {},
};

interface SettingsState {
  settings: Settings;
  isLoading: boolean;
  loadSettings: () => Promise<void>;
  updateSettings: (partial: Partial<Settings>) => Promise<void>;
}

export const useSettingsStore = create<SettingsState>((set) => ({
  settings: defaultSettings,
  isLoading: false,

  loadSettings: async () => {
    set({ isLoading: true });
    try {
      const res = await api.get('/settings');
      const data = res.data?.data || res.data || null;
      if (data) set({ settings: { ...defaultSettings, ...data } });
    } catch {
      // use defaults
    } finally {
      set({ isLoading: false });
    }
  },

  updateSettings: async (partial) => {
    set((s) => ({ settings: { ...s.settings, ...partial } }));
    try {
      await api.put('/settings', partial);
    } catch {
      // handled silently
    }
  },
}));
