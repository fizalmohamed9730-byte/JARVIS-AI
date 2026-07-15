import { useCallback, useEffect, useRef } from 'react';
import { useVoiceStore } from '@/stores/voiceStore';

export function useVoice() {
  const store = useVoiceStore();
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    return () => {
      store.cleanup();
    };
  }, []);

  const startListening = useCallback(async () => {
    const SpeechRecognitionAPI = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognitionAPI) {
      console.warn('Speech Recognition not supported');
      await store.startListening();
      return;
    }

    const recognition = new SpeechRecognitionAPI();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onresult = (event: any) => {
      let interimTranscript = '';
      let finalTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript;
        } else {
          interimTranscript += transcript;
        }
      }

      store.setTranscript(finalTranscript || interimTranscript);
      store.setConfidence(event.results[event.results.length - 1]?.[0].confidence || 0);

      if (finalTranscript.toLowerCase().includes('hey jarvis')) {
        store.setWakeWordDetected(true);
      }
    };

    recognition.onerror = (event: any) => {
      console.error('Speech recognition error:', event.error);
      store.setListening(false);
    };

    recognition.onend = () => {
      store.setListening(false);
    };

    recognitionRef.current = recognition;
    recognition.start();
    store.setListening(true);
  }, []);

  const stopListening = useCallback(() => {
    recognitionRef.current?.stop();
    recognitionRef.current = null;
    store.stopListening();
  }, []);

  const interrupt = useCallback(() => {
    recognitionRef.current?.stop();
    recognitionRef.current = null;
    store.interrupt();
    window.speechSynthesis?.cancel();
  }, []);

  return {
    isListening: store.isListening,
    isSpeaking: store.isSpeaking,
    isProcessing: store.isProcessing,
    transcript: store.transcript,
    wakeWordDetected: store.wakeWordDetected,
    startListening,
    stopListening,
    interrupt,
  };
}

declare global {
  interface Window {
    SpeechRecognition: any;
    webkitSpeechRecognition: any;
  }
}
