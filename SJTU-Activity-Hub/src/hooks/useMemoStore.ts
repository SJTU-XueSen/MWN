import { create } from "zustand";
import type { MemoItem } from "../../shared/memos";

type MemoState = {
  memos: MemoItem[];
  loading: boolean;
  fetchMemos: () => Promise<void>;
  addMemo: (title: string, note: string, deadline: string) => Promise<void>;
  removeMemo: (id: string) => Promise<void>;
};

export const useMemoStore = create<MemoState>((set) => ({
  memos: [],
  loading: false,
  fetchMemos: async () => {
    set({ loading: true });
    try {
      const response = await fetch("/api/memos");
      const data = (await response.json()) as { success: boolean; items: MemoItem[] };
      if (data.success) {
        set({ memos: data.items });
      }
    } catch {
      // 静默失败
    } finally {
      set({ loading: false });
    }
  },
  addMemo: async (title, note, deadline) => {
    try {
      const response = await fetch("/api/memos", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, note, deadline }),
      });
      const data = (await response.json()) as { success: boolean; item: MemoItem };
      if (data.success) {
        set((state) => ({ memos: [data.item, ...state.memos] }));
      }
    } catch {
      // 静默失败
    }
  },
  removeMemo: async (id) => {
    try {
      await fetch(`/api/memos/${id}`, { method: "DELETE" });
      set((state) => ({ memos: state.memos.filter((m) => m.id !== id) }));
    } catch {
      // 静默失败
    }
  },
}));
