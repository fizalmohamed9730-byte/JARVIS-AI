import { useEffect, lazy, Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import HomeDashboard from './pages/HomeDashboard';
import Dock from './components/Dock';
import FloatingVoiceButton from './components/FloatingVoiceButton';
import ErrorBoundary from './components/ErrorBoundary';
import { useSettingsStore } from './stores/settingsStore';
import { ThemeProvider } from './theme/ThemeProvider';

const ChatPage = lazy(() => import('./pages/ChatPage'));
const TasksPage = lazy(() => import('./pages/TasksPage'));
const NotesPage = lazy(() => import('./pages/NotesPage'));
const CalendarPage = lazy(() => import('./pages/CalendarPage'));
const EmailPage = lazy(() => import('./pages/EmailPage'));
const SettingsPage = lazy(() => import('./pages/SettingsPage'));
const MemoryViewer = lazy(() => import('./components/MemoryViewer'));
const AutomationPanel = lazy(() => import('./components/AutomationPanel'));
const FileManagerPage = lazy(() => import('./pages/FileManagerPage'));
const ImageGenerationPage = lazy(() => import('./pages/ImageGenerationPage'));
const WebsiteGeneratorPage = lazy(() => import('./pages/WebsiteGeneratorPage'));
const VideoWorkflowPage = lazy(() => import('./pages/VideoWorkflowPage'));
const AuthPage = lazy(() => import('./pages/AuthPage'));

export default function App() {
  const loadSettings = useSettingsStore((s) => s.loadSettings);

  useEffect(() => {
    loadSettings();
  }, []);

  return (
    <ErrorBoundary>
      <ThemeProvider>
        <div className="min-h-screen relative" style={{ background: 'var(--bg-base)', color: 'var(--text-primary)' }}>
          <Layout>
            <Dock />
            <Suspense fallback={<div className="flex h-full items-center justify-center"><div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" /></div>}>
              <Routes>
                <Route path="/" element={<HomeDashboard />} />
                <Route path="/auth" element={<AuthPage />} />
                <Route path="/chat" element={<ChatPage />} />
                <Route path="/tasks" element={<TasksPage />} />
                <Route path="/notes" element={<NotesPage />} />
                <Route path="/calendar" element={<CalendarPage />} />
                <Route path="/email" element={<EmailPage />} />
                <Route path="/settings" element={<SettingsPage />} />
                <Route path="/memory" element={<MemoryViewer />} />
                <Route path="/automation" element={<AutomationPanel />} />
                <Route path="/files" element={<FileManagerPage />} />
                <Route path="/images" element={<ImageGenerationPage />} />
                <Route path="/websites" element={<WebsiteGeneratorPage />} />
                <Route path="/video" element={<VideoWorkflowPage />} />
                <Route path="*" element={<HomeDashboard />} />
              </Routes>
            </Suspense>
            <FloatingVoiceButton />
          </Layout>
        </div>
      </ThemeProvider>
    </ErrorBoundary>
  );
}
