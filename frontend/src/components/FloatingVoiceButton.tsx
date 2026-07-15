import { Mic } from 'lucide-react';
import { useVoice } from '../hooks/useVoice';

export default function FloatingVoiceButton() {
  const { isListening, startListening, stopListening } = useVoice();

  return (
    <button
      onClick={() => (isListening ? stopListening() : startListening())}
      className={`fixed bottom-6 right-6 z-50 w-14 h-14 rounded-full flex items-center justify-center shadow-xl transition-all duration-300 ${
        isListening
          ? 'bg-red-600 animate-pulse scale-110'
          : 'bg-blue-600 hover:bg-blue-500'
      }`}
      title={isListening ? 'Stop listening' : 'Start voice input'}
    >
      <Mic className="w-6 h-6 text-white" />
    </button>
  );
}
