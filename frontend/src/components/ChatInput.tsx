import { useState, useRef, useCallback } from 'react';
import { Send, Mic, Paperclip } from 'lucide-react';
import { useVoice } from '@/hooks/useVoice';
import clsx from 'clsx';

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

export default function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { isListening, transcript, startListening, stopListening } = useVoice();

  const handleSend = useCallback(() => {
    const text = (value || transcript).trim();
    if (!text || disabled) return;
    onSend(text);
    setValue('');
    if (isListening) stopListening();
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [value, transcript, disabled, onSend, isListening, stopListening]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setValue(e.target.value);
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  };

  return (
    <div className="glass rounded-2xl p-2 input-glow transition-all">
      <div className="flex items-end gap-2">
        <button className="mb-2 rounded-lg p-2 text-gray-400 transition-colors hover:bg-white/10 hover:text-white">
          <Paperclip className="h-5 w-5" />
        </button>
        <textarea
          ref={textareaRef}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={isListening ? 'Listening...' : 'Message JARVIS...'}
          rows={1}
          disabled={disabled}
          className="max-h-[200px] min-h-[40px] flex-1 resize-none bg-transparent px-2 py-2.5 text-sm text-gray-100 placeholder-gray-500 outline-none"
        />
        <button
          onClick={isListening ? stopListening : startListening}
          className={clsx(
            'mb-2 rounded-lg p-2 transition-all',
            isListening
              ? 'bg-blue-500/20 text-blue-400 animate-pulse-glow'
              : 'text-gray-400 hover:bg-white/10 hover:text-white',
          )}
        >
          <Mic className="h-5 w-5" />
        </button>
        <button
          onClick={handleSend}
          disabled={disabled || (!(value || transcript).trim())}
          className={clsx(
            'mb-2 rounded-lg p-2 transition-all',
            (value || transcript).trim()
              ? 'bg-blue-500 text-white hover:bg-blue-600'
              : 'text-gray-500',
          )}
        >
          <Send className="h-5 w-5" />
        </button>
      </div>
      {isListening && transcript && (
        <div className="border-t border-white/5 px-3 py-1.5 text-xs text-blue-400/80">{transcript}</div>
      )}
    </div>
  );
}
