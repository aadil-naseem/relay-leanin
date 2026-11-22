import { create } from 'zustand'

const STORAGE_KEY = 'relay-ui-preferences'

const defaults = {
  highContrast: false,
  reduceMotion: false,
  sceneTier: 'auto',
  backdrop: true,
  sound: false,
  presenterMode: false,
  presenterStep: 0,
  presenterHidden: false,
  presenterRecoveryId: null,
  snapshotMode: false,
}

function readPreferences() {
  try {
    const saved = JSON.parse(window.localStorage.getItem(STORAGE_KEY) || '{}')
    return Object.fromEntries(Object.keys(defaults).map((key) => [key, saved[key] ?? defaults[key]]))
  } catch {
    return defaults
  }
}

export const useUiStore = create((set) => ({
  ...defaults,
  ...readPreferences(),
  setPreference: (key, value) => set({ [key]: value }),
  goToPresenterStep: (step) => set({
    presenterStep: Math.max(0, Math.min(7, step)),
    presenterHidden: false,
  }),
}))

useUiStore.subscribe((state) => {
  try {
    const preferences = Object.fromEntries(Object.keys(defaults).map((key) => [key, state[key]]))
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(preferences))
  } catch {
    // Storage is an optional convenience; the UI works without it.
  }
})
