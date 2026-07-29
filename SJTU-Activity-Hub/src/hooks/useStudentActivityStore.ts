import { create } from "zustand";
import type { StudentActivity } from "../../shared/studentActivities";

type State = {
  items: StudentActivity[];
  loading: boolean;
  fetchAll: () => Promise<void>;
  submit: (data: {
    title: string;
    description: string;
    date: string;
    location: string;
    organizer: string;
    contact: string;
  }) => Promise<boolean>;
  remove: (id: string) => Promise<void>;
};

export const useStudentActivityStore = create<State>((set) => ({
  items: [],
  loading: false,
  fetchAll: async () => {
    set({ loading: true });
    try {
      const res = await fetch("/api/student-activities");
      const data = (await res.json()) as { success: boolean; items: StudentActivity[] };
      if (data.success) set({ items: data.items });
    } catch {
      // 静默
    } finally {
      set({ loading: false });
    }
  },
  submit: async (form) => {
    try {
      const res = await fetch("/api/student-activities", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      const data = (await res.json()) as { success: boolean; item: StudentActivity; error?: string };
      if (data.success) {
        set((s) => ({ items: [data.item, ...s.items] }));
        return true;
      }
      return false;
    } catch {
      return false;
    }
  },
  remove: async (id) => {
    try {
      await fetch(`/api/student-activities/${id}`, { method: "DELETE" });
      set((s) => ({ items: s.items.filter((i) => i.id !== id) }));
    } catch {
      // 静默
    }
  },
}));
