import { create } from "zustand";
import type { ConfirmedNotification } from "../../shared/notifications";

type NotificationState = {
  notifications: ConfirmedNotification[];
  loading: boolean;
  fetchNotifications: () => Promise<void>;
  confirmNotification: (item: ConfirmedNotification) => Promise<void>;
  removeNotification: (id: string) => Promise<void>;
};

export const useNotificationStore = create<NotificationState>((set, get) => ({
  notifications: [],
  loading: false,
  fetchNotifications: async () => {
    try {
      const response = await fetch("/api/notifications");
      const data = (await response.json()) as { success: boolean; items: ConfirmedNotification[] };
      if (data.success) {
        set({ notifications: data.items });
      }
    } catch {
      // 静默失败
    }
  },
  confirmNotification: async (item) => {
    const existing = get().notifications.some((n) => n.id === item.id);
    if (existing) return;

    try {
      const response = await fetch("/api/notifications", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(item),
      });
      const data = (await response.json()) as { success: boolean; item: ConfirmedNotification };
      if (data.success) {
        set((state) => ({ notifications: [data.item, ...state.notifications] }));
      }
    } catch {
      // 静默失败
    }
  },
  removeNotification: async (id) => {
    try {
      await fetch(`/api/notifications/${id}`, { method: "DELETE" });
      set((state) => ({
        notifications: state.notifications.filter((n) => n.id !== id),
      }));
    } catch {
      // 静默失败
    }
  },
}));

type AiSearchResponse = {
  recommendations: ConfirmedNotification[];
  campusCount: number;
  webCount: number;
  reasoning: string;
};

type AiSearchState = {
  query: string;
  reasoning: string;
  recommendations: ConfirmedNotification[];
  campusCount: number;
  webCount: number;
  loading: boolean;
  searched: boolean;
  setQuery: (query: string) => void;
  search: () => Promise<void>;
  reset: () => void;
};

export const useAiSearchStore = create<AiSearchState>((set, get) => ({
  query: "",
  reasoning: "",
  recommendations: [],
  campusCount: 0,
  webCount: 0,
  loading: false,
  searched: false,
  setQuery: (query) => set({ query }),
  search: async () => {
    const { query } = get();
    if (!query.trim()) return;

    set({ loading: true, searched: false, recommendations: [], reasoning: "" });

    try {
      const response = await fetch("/api/ai-search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query.trim() }),
      });

      const data = (await response.json()) as AiSearchResponse & { success?: boolean };

      set({
        recommendations: data.recommendations || [],
        reasoning: data.reasoning || "",
        campusCount: data.campusCount || 0,
        webCount: data.webCount || 0,
        searched: true,
        loading: false,
      });
    } catch {
      set({ loading: false, searched: true, reasoning: "搜索请求失败，请稍后重试。" });
    }
  },
  reset: () =>
    set({ query: "", recommendations: [], reasoning: "", searched: false, campusCount: 0, webCount: 0 }),
}));
