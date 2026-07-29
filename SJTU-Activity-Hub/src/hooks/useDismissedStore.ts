import { useCallback, useSyncExternalStore } from "react";

const STORAGE_KEY = "compete_dismissed_ids";

let cachedRaw: string | null = null;
let cachedSet: Set<string> = new Set();

function readRaw(): string {
  try {
    return localStorage.getItem(STORAGE_KEY) ?? "[]";
  } catch {
    return "[]";
  }
}

function getSnapshot(): Set<string> {
  const raw = readRaw();
  if (raw !== cachedRaw) {
    cachedRaw = raw;
    try {
      cachedSet = new Set(JSON.parse(raw) as string[]);
    } catch {
      cachedSet = new Set();
    }
  }
  return cachedSet;
}

function subscribe(callback: () => void) {
  const handler = (e: StorageEvent) => {
    if (e.key === STORAGE_KEY) {
      cachedRaw = null; // invalidate cache
      callback();
    }
  };
  window.addEventListener("storage", handler);
  return () => window.removeEventListener("storage", handler);
}

function persist(ids: Set<string>) {
  const raw = JSON.stringify(Array.from(ids));
  cachedRaw = raw;
  cachedSet = new Set(ids);
  localStorage.setItem(STORAGE_KEY, raw);
  window.dispatchEvent(new StorageEvent("storage", { key: STORAGE_KEY }));
}

export function useDismissedStore() {
  const dismissed = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);

  const dismiss = useCallback((id: string) => {
    const next = new Set(getSnapshot());
    next.add(id);
    persist(next);
  }, []);

  const restore = useCallback((id: string) => {
    const next = new Set(getSnapshot());
    next.delete(id);
    persist(next);
  }, []);

  const isDismissed = useCallback((id: string) => dismissed.has(id), [dismissed]);

  return { dismissed, dismiss, restore, isDismissed };
}
