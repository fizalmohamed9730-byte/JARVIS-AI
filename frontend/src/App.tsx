import { Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import ChatPage from './pages/ChatPage';
import TasksPage from './pages/TasksPage';
import NotesPage from './pages/NotesPage';
import CalendarPage from './pages/CalendarPage';
import EmailPage from './pages/EmailPage';
import SettingsPage from './pages/SettingsPage';
import MemoryViewer from './components/MemoryViewer';
import AutomationPanel from './components/AutomationPanel';
import FileManagerPage from './pages/FileManagerPage';
import ImageGenerationPage from './pages/ImageGenerationPage';
import WebsiteGeneratorPage from './pages/WebsiteGeneratorPage';
import VideoWorkflowPage from './pages/VideoWorkflowPage';

export default function App() {
  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <Layout>
        <Routes>
          <Route path="/" element={<ChatPage />} />
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
          <Route path="*" element={<ChatPage />} />
        </Routes>
      </Layout>
    </div>
  );
}
