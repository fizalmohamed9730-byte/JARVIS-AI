import { create } from 'zustand';
import type { VoiceStatus } from '@/types';

interface VoiceState extends VoiceStatus {
  mediaRecorder: MediaRecorder | null;
  audioContext: AudioContext | null;

  setListening: (listening: boolean) => void;
  setSpeaking: (speaking: boolean) => void;
  setProcessing: (processing: boolean) => void;
  setTranscript: (transcript: string) => void;
  setWakeWordDetected: (detected: boolean) => void;
  setConfidence: (confidence: number) => void;
  startListening: () => Promise<void>;
  stopListening: () => void;
  interrupt: () => void;
  cleanup: () => void;
}

export const useVoiceStore = create<VoiceState>((set, get) => ({
  isListening: false,
  isSpeaking: false,
  isProcessing: false,
  transcript: '',
  wakeWordDetected: false,
  confidence: 0,
  mediaRecorder: null,
  audioContext: null,

  setListening: (isListening) => set({ isListening }),
  setSpeaking: (isSpeaking) => set({ isSpeaking }),
  setProcessing: (isProcessing) => set({ isProcessing }),
  setTranscript: (transcript) => set({ transcript }),
  setWakeWordDetected: (wakeWordDetected) => set({ wakeWordDetected }),
  setConfidence: (confidence) => set({ confidence }),

  startListening: async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const audioContext = new AudioContext();
      const mediaRecorder = new MediaRecorder(stream);

      set({ mediaRecorder, audioContext, isListening: true });

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          // Audio data would be sent to STT service
        }
      };

      mediaRecorder.start(1000);
    } catch (error) {
      console.error('Failed to start listening:', error);
      set({ isListening: false });
    }
  },

  stopListening: () => {
    const { mediaRecorder, audioContext } = get();
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
      mediaRecorder.stream.getTracks().forEach((t) => t.stop());
    }
    audioContext?.close();
    set({ mediaRecorder: null, audioContext: null, isListening: false });
  },

  interrupt: () => {
    const { mediaRecorder } = get();
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
      mediaRecorder.stream.getTracks().forEach((t) => t.stop());
    }
    set({ isSpeaking: false, isListening: false });
  },

  cleanup: () => {
    const { mediaRecorder, audioContext } = get();
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
      mediaRecorder.stream.getTracks().forEach((t) => t.stop());
    }
    audioContext?.close();
    set({
      mediaRecorder: null,
      audioContext: null,
      isListening: false,
      isSpeaking: false,
      isProcessing: false,
      transcript: '',
      wakeWordDetected: false,
    });
  },
}));
