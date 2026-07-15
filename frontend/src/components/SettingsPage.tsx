import { useState } from 'react';
import { useSettingsStore } from '@/stores/settingsStore';
import { User, Mic, Brain, Palette, Bell, Key, Save } from 'lucide-react';
import clsx from 'clsx';
import toast from 'react-hot-toast';

type Tab = 'profile' | 'voice' | 'ai' | 'theme' | 'notifications' | 'apikeys';

const tabs: { id: Tab; label: string; icon: React.ElementType }[] = [
  { id: 'profile', label: 'Profile', icon: User },
  { id: 'voice', label: 'Voice', icon: Mic },
  { id: 'ai', label: 'AI', icon: Brain },
  { id: 'theme', label: 'Theme', icon: Palette },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'apikeys', label: 'API Keys', icon: Key },
];

export default function SettingsPageComponent() {
  const { settings, updateSettings } = useSettingsStore();
  const [activeTab, setActiveTab] = useState<Tab>('profile');

  const handleSave = async () => {
    await updateSettings(settings);
    toast.success('Settings saved');
  };

  return (
    <div className="mx-auto max-w-4xl">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-white">Settings</h1>
        <p className="text-sm text-gray-500">Configure your JARVIS experience</p>
      </div>

      <div className="flex gap-6">
        {/* Tabs */}
        <nav className="w-48 flex-shrink-0 space-y-1">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={clsx(
                'flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all',
                activeTab === tab.id ? 'bg-blue-500/15 text-blue-400' : 'text-gray-400 hover:bg-white/5 hover:text-gray-200',
              )}
            >
              <tab.icon className="h-4 w-4" />
              {tab.label}
            </button>
          ))}
        </nav>

        {/* Content */}
        <div className="flex-1 glass rounded-xl p-6">
          {activeTab === 'profile' && (
            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-white">Profile Settings</h3>
              <div className="flex items-center gap-4">
                <div className="flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-blue-700 text-xl font-bold">J</div>
                <button className="rounded-lg border border-white/10 px-3 py-1.5 text-xs text-gray-400 hover:bg-white/5">Change Avatar</button>
              </div>
              <div>
                <label className="mb-1 block text-xs text-gray-500">Name</label>
                <input value={settings.profile.name} onChange={(e) => updateSettings({ profile: { ...settings.profile, name: e.target.value } })} className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-blue-500/50" />
              </div>
              <div>
                <label className="mb-1 block text-xs text-gray-500">Email</label>
                <input value={settings.profile.email} onChange={(e) => updateSettings({ profile: { ...settings.profile, email: e.target.value } })} className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-blue-500/50" />
              </div>
            </div>
          )}

          {activeTab === 'voice' && (
            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-white">Voice Settings</h3>
              <Toggle label="Voice Enabled" checked={settings.voice.enabled} onChange={(v) => updateSettings({ voice: { ...settings.voice, enabled: v } })} />
              <div>
                <label className="mb-1 block text-xs text-gray-500">Wake Word</label>
                <input value={settings.voice.wakeWord} onChange={(e) => updateSettings({ voice: { ...settings.voice, wakeWord: e.target.value } })} className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-blue-500/50" />
              </div>
              <div>
                <label className="mb-1 block text-xs text-gray-500">Speed: {settings.voice.speed.toFixed(1)}x</label>
                <input type="range" min="0.5" max="2" step="0.1" value={settings.voice.speed} onChange={(e) => updateSettings({ voice: { ...settings.voice, speed: parseFloat(e.target.value) } })} className="w-full accent-blue-500" />
              </div>
              <div>
                <label className="mb-1 block text-xs text-gray-500">Language</label>
                <select value={settings.voice.language} onChange={(e) => updateSettings({ voice: { ...settings.voice, language: e.target.value } })} className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-blue-500/50">
                  <option value="en-US">English (US)</option>
                  <option value="en-GB">English (UK)</option>
                  <option value="es-ES">Spanish</option>
                  <option value="fr-FR">French</option>
                  <option value="de-DE">German</option>
                  <option value="ja-JP">Japanese</option>
                </select>
              </div>
              <Toggle label="Continuous Mode" checked={settings.voice.continuousMode} onChange={(v) => updateSettings({ voice: { ...settings.voice, continuousMode: v } })} />
            </div>
          )}

          {activeTab === 'ai' && (
            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-white">AI Settings</h3>
              <div>
                <label className="mb-1 block text-xs text-gray-500">Model</label>
                <select value={settings.ai.selectedModel} onChange={(e) => updateSettings({ ai: { ...settings.ai, selectedModel: e.target.value } })} className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-blue-500/50">
                  <option value="gpt-4">GPT-4</option>
                  <option value="gpt-4-turbo">GPT-4 Turbo</option>
                  <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                  <option value="claude-3-opus">Claude 3 Opus</option>
                  <option value="claude-3-sonnet">Claude 3 Sonnet</option>
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs text-gray-500">Temperature: {settings.ai.temperature.toFixed(1)}</label>
                <input type="range" min="0" max="2" step="0.1" value={settings.ai.temperature} onChange={(e) => updateSettings({ ai: { ...settings.ai, temperature: parseFloat(e.target.value) } })} className="w-full accent-blue-500" />
              </div>
              <div>
                <label className="mb-1 block text-xs text-gray-500">Max Tokens</label>
                <input type="number" value={settings.ai.maxTokens} onChange={(e) => updateSettings({ ai: { ...settings.ai, maxTokens: parseInt(e.target.value) } })} className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-blue-500/50" />
              </div>
            </div>
          )}

          {activeTab === 'theme' && (
            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-white">Theme Settings</h3>
              <div>
                <label className="mb-1 block text-xs text-gray-500">Font Size</label>
                <div className="flex gap-2">
                  {(['sm', 'md', 'lg'] as const).map((size) => (
                    <button key={size} onClick={() => updateSettings({ theme: { ...settings.theme, fontSize: size } })} className={clsx('rounded-lg px-4 py-2 text-sm transition-all', settings.theme.fontSize === size ? 'bg-blue-500/20 text-blue-400 ring-1 ring-blue-500/50' : 'bg-white/5 text-gray-400 hover:bg-white/10')}>
                      {size.toUpperCase()}
                    </button>
                  ))}
                </div>
              </div>
              <Toggle label="Animations" checked={settings.theme.animations} onChange={(v) => updateSettings({ theme: { ...settings.theme, animations: v } })} />
            </div>
          )}

          {activeTab === 'notifications' && (
            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-white">Notification Settings</h3>
              <Toggle label="Desktop Notifications" checked={settings.notifications.desktop} onChange={(v) => updateSettings({ notifications: { ...settings.notifications, desktop: v } })} />
              <Toggle label="Sound" checked={settings.notifications.sound} onChange={(v) => updateSettings({ notifications: { ...settings.notifications, sound: v } })} />
              <Toggle label="Email Digest" checked={settings.notifications.emailDigest} onChange={(v) => updateSettings({ notifications: { ...settings.notifications, emailDigest: v } })} />
            </div>
          )}

          {activeTab === 'apikeys' && (
            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-white">API Keys</h3>
              <p className="text-xs text-gray-500">Enter your API keys for various AI providers.</p>
              {(['openai', 'anthropic', 'google'] as const).map((key) => (
                <div key={key}>
                  <label className="mb-1 block text-xs text-gray-500 capitalize">{key}</label>
                  <input type="password" placeholder={`Enter ${key} API key...`} value={settings.apiKeys[key] || ''} onChange={(e) => updateSettings({ apiKeys: { ...settings.apiKeys, [key]: e.target.value } })} className="w-full rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-sm text-white outline-none focus:border-blue-500/50" />
                </div>
              ))}
            </div>
          )}

          <div className="mt-6 border-t border-white/10 pt-4">
            <button onClick={handleSave} className="flex items-center gap-2 rounded-lg bg-blue-500 px-4 py-2 text-sm font-medium text-white hover:bg-blue-600">
              <Save className="h-4 w-4" />
              Save Changes
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function Toggle({ label, checked, onChange }: { label: string; checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-gray-300">{label}</span>
      <button
        onClick={() => onChange(!checked)}
        className={clsx(
          'relative h-6 w-11 rounded-full transition-colors',
          checked ? 'bg-blue-500' : 'bg-gray-600',
        )}
      >
        <div className={clsx('absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform', checked ? 'translate-x-[22px]' : 'translate-x-0.5')} />
      </button>
    </div>
  );
}
