import ChatInterface from '@/components/ChatInterface';
import VoiceVisualizer from '@/components/VoiceVisualizer';

export default function ChatPage() {
  return (
    <div className="flex h-full gap-4">
      <div className="flex-1">
        <ChatInterface />
      </div>
      <div className="hidden w-48 flex-shrink-0 lg:block">
        <VoiceVisualizer />
      </div>
    </div>
  );
}
