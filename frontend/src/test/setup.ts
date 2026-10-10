// Copyright (C) 2024 Shatter-NC contributors
// SPDX-License-Identifier: AGPL-3.0-or-later

import '@testing-library/jest-dom';

// Node ≥25 ships a global `localStorage` stub (no --localstorage-file) that shadows
// jsdom's and has no methods. Swap in an in-memory Storage only when it is unusable.
class MemoryStorage implements Storage {
  private data = new Map<string, string>();
  get length() {
    return this.data.size;
  }
  clear() {
    this.data.clear();
  }
  getItem(key: string) {
    return this.data.has(key) ? (this.data.get(key) as string) : null;
  }
  key(index: number) {
    return Array.from(this.data.keys())[index] ?? null;
  }
  removeItem(key: string) {
    this.data.delete(key);
  }
  setItem(key: string, value: string) {
    this.data.set(key, String(value));
  }
}

try {
  globalThis.localStorage.clear();
} catch {
  const storage = new MemoryStorage();
  for (const target of [globalThis, typeof window !== 'undefined' ? window : undefined]) {
    if (target) Object.defineProperty(target, 'localStorage', { value: storage, configurable: true });
  }
}
