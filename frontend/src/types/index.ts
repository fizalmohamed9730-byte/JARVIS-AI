export interface User {
  id: string;
  name: string;
  email: string;
  avatar?: string;
  preferences: UserPreferences;
  createdAt: string;
}

export interface UserPreferences {
  theme: 'dark' | 'light';
  voiceEnabled: boolean;
  wakeWord: string;
  language: string;
  voiceSpeed: number;
  notifications: boolean;
}

export interface Conversation {
  id: string;
  title: string;
  lastMessage: string;
  lastMessageAt: string;
  messageCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface Message {
  id: string;
  conversationId: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  isStreaming?: boolean;
  metadata?: MessageMetadata;
}

export interface MessageMetadata {
  sources?: string[];
  tokens?: number;
  model?: string;
  latency?: number;
}

export interface Task {
  id: string;
  title: string;
  description?: string;
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled';
  priority: 'low' | 'medium' | 'high' | 'urgent';
  dueDate?: string;
  tags: string[];
  createdAt: string;
  updatedAt: string;
}

export interface Note {
  id: string;
  title: string;
  content: string;
  tags: string[];
  pinned: boolean;
  color?: string;
  createdAt: string;
  updatedAt: string;
}

export interface Reminder {
  id: string;
  title: string;
  message?: string;
  datetime: string;
  recurring: boolean;
  recurringPattern?: 'daily' | 'weekly' | 'monthly';
  completed: boolean;
  createdAt: string;
}

export interface Email {
  id: string;
  from: string;
  fromName: string;
  to: string[];
  subject: string;
  body: string;
  snippet: string;
  read: boolean;
  starred: boolean;
  category: 'primary' | 'social' | 'promotions' | 'updates' | 'spam';
  date: string;
  attachments?: EmailAttachment[];
}

export interface EmailAttachment {
  filename: string;
  size: number;
  mimeType: string;
  url: string;
}

export interface CalendarEvent {
  id: string;
  title: string;
  description?: string;
  startDate: string;
  endDate: string;
  allDay: boolean;
  color: string;
  location?: string;
  reminders: EventReminder[];
  createdAt: string;
}

export interface EventReminder {
  minutes: number;
  method: 'notification' | 'email';
}

export interface Memory {
  id: string;
  category: 'preference' | 'fact' | 'context' | 'relationship' | 'habit';
  key: string;
  value: string;
  confidence: number;
  source: string;
  createdAt: string;
  updatedAt: string;
}

export interface Automation {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  trigger: AutomationTrigger;
  actions: AutomationAction[];
  lastRun?: string;
  createdAt: string;
}

export interface AutomationTrigger {
  type: 'schedule' | 'event' | 'command' | 'webhook';
  config: Record<string, unknown>;
}

export interface AutomationAction {
  type: string;
  config: Record<string, unknown>;
}

export interface ActionLog {
  id: string;
  automationId?: string;
  type: string;
  status: 'success' | 'failure' | 'pending';
  details: string;
  timestamp: string;
}

export interface WebSocketEvent {
  type: 'message' | 'typing' | 'stream_start' | 'stream_chunk' | 'stream_end' | 'error' | 'voice_state' | 'notification';
  payload: unknown;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  error?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

export interface VoiceStatus {
  isListening: boolean;
  isSpeaking: boolean;
  isProcessing: boolean;
  transcript: string;
  wakeWordDetected: boolean;
  confidence: number;
}

export interface Settings {
  profile: {
    name: string;
    email: string;
    avatar?: string;
  };
  voice: {
    enabled: boolean;
    language: string;
    speed: number;
    wakeWord: string;
    continuousMode: boolean;
  };
  ai: {
    onlinePreference: 'always' | 'when-needed' | 'never';
    selectedModel: string;
    temperature: number;
    maxTokens: number;
  };
  theme: {
    mode: 'dark' | 'light';
    accentColor: string;
    fontSize: 'sm' | 'md' | 'lg';
    animations: boolean;
  };
  notifications: {
    desktop: boolean;
    sound: boolean;
    emailDigest: boolean;
  };
  apiKeys: {
    openai?: string;
    anthropic?: string;
    google?: string;
  };
}

export interface FileItem {
  name: string;
  path: string;
  type: 'file' | 'directory';
  size: number;
  modified: string;
  extension: string;
}

export interface GeneratedImage {
  id: string;
  prompt: string;
  url: string;
  style: string;
  size: string;
  provider: string;
  created_at: string;
  status: string;
}

export interface WebsiteProject {
  id: string;
  prompt: string;
  style: string;
  framework: string;
  files: { filename: string; content: string; type: string }[];
  preview_html: string;
  created_at: string;
  status: string;
}

export interface VideoProject {
  id: string;
  title: string;
  description?: string;
  script?: string;
  style: string;
  duration: string;
  provider: string;
  scenes: VideoScene[];
  status: string;
  progress: number;
  created_at: string;
  updated_at: string;
}

export interface VideoScene {
  scene_number: number;
  title: string;
  description: string;
  duration_seconds: number;
  narration: string;
  visual_prompt: string;
  transition: string;
}
