'use client';

import { create } from 'zustand';

import type { SceneScript } from './types';

interface AppState {
  sessionId: string;
  scene: SceneScript | null;
  selectedObjectId: string | null;
  statusText: string;
  setSessionId: (sessionId: string) => void;
  setScene: (scene: SceneScript | null) => void;
  setSelectedObjectId: (objectId: string | null) => void;
  setStatusText: (status: string) => void;
}

export const useAppStore = create<AppState>((set) => ({
  sessionId: 'demo-session',
  scene: null,
  selectedObjectId: null,
  statusText: 'Idle',
  setSessionId: (sessionId) => set({ sessionId }),
  setScene: (scene) => set({ scene }),
  setSelectedObjectId: (selectedObjectId) => set({ selectedObjectId }),
  setStatusText: (statusText) => set({ statusText })
}));
