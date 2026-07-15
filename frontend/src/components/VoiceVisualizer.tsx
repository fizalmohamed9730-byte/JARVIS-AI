import { useVoice } from '@/hooks/useVoice';
import clsx from 'clsx';

export default function VoiceVisualizer() {
  const { isListening, isSpeaking, isProcessing } = useVoice();

  const bars = 5;

  return (
    <div className="flex flex-col items-center gap-4 py-6">
      {/* Central orb */}
      <div className="relative">
        {/* Background rings */}
        {isListening && (
          <>
            <div className="absolute inset-0 rounded-full border border-blue-500/20 voice-ring" style={{ animationDelay: '0s' }} />
            <div className="absolute inset-0 rounded-full border border-blue-500/15 voice-ring" style={{ animationDelay: '0.5s' }} />
            <div className="absolute inset-0 rounded-full border border-blue-500/10 voice-ring" style={{ animationDelay: '1s' }} />
          </>
        )}

        {/* Main orb */}
        <div
          className={clsx(
            'relative flex h-20 w-20 items-center justify-center rounded-full transition-all duration-300',
            isListening && 'bg-blue-500/20 animate-pulse-glow',
            isSpeaking && 'bg-blue-500/30',
            isProcessing && 'bg-arc-500/20',
            !isListening && !isSpeaking && !isProcessing && 'bg-white/5',
          )}
        >
          {/* Waveform bars */}
          <div className="flex items-center gap-1">
            {Array.from({ length: bars }).map((_, i) => (
              <div
                key={i}
                className={clsx(
                  'w-1 rounded-full transition-all',
                  isListening || isSpeaking ? 'bg-blue-400 animate-wave' : 'bg-gray-600 h-2',
                )}
                style={{
                  height: isListening || isSpeaking ? `${12 + Math.random() * 16}px` : '8px',
                  animationDelay: `${i * 0.1}s`,
                  animationDuration: isSpeaking ? '0.8s' : '1.5s',
                }}
              />
            ))}
          </div>

          {/* Status indicator */}
          {isProcessing && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="h-6 w-6 animate-spin rounded-full border-2 border-arc-400 border-t-transparent" />
            </div>
          )}
        </div>
      </div>

      {/* Status text */}
      <div className="text-center">
        <p className={clsx(
          'text-xs font-medium uppercase tracking-wider',
          isListening && 'text-blue-400',
          isSpeaking && 'text-blue-300',
          isProcessing && 'text-arc-400',
          !isListening && !isSpeaking && !isProcessing && 'text-gray-600',
        )}>
          {isListening ? 'Listening...' : isSpeaking ? 'Speaking...' : isProcessing ? 'Processing...' : 'Idle'}
        </p>
      </div>
    </div>
  );
}
