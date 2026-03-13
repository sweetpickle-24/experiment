import { create } from 'zustand';
import type { WaveSnapshot } from '../types/brain';

interface BrainStore {
  snapshot: WaveSnapshot | null;
  isConnected: boolean;
  history: WaveSnapshot[];
  maxHistory: number;
  
  setSnapshot: (snapshot: WaveSnapshot) => void;
  setConnected: (connected: boolean) => void;
  clearHistory: () => void;
}

export const useBrainStore = create<BrainStore>((set) => ({
  snapshot: null,
  isConnected: false,
  history: [],
  maxHistory: 100,
  
  setSnapshot: (snapshot) => set((state) => ({
    snapshot,
    history: [...state.history.slice(-state.maxHistory + 1), snapshot],
  })),
  
  setConnected: (connected) => set({ isConnected: connected }),
  
  clearHistory: () => set({ history: [] }),
}));
