import { create } from "zustand";
import type { ActivitiesResponse } from "../../shared/activities";

type ActivitiesState = {
  data: ActivitiesResponse | null;
  error: string | null;
  loading: boolean;
  selectedId: string | null;
  fetchActivities: () => Promise<void>;
  selectActivity: (id: string | null) => void;
};

export const useActivitiesStore = create<ActivitiesState>((set, get) => ({
  data: null,
  error: null,
  loading: false,
  selectedId: null,
  fetchActivities: async () => {
    if (get().loading) {
      return;
    }

    set({ loading: true, error: null });

    try {
      const response = await fetch("/api/activities");

      if (!response.ok) {
        throw new Error("接口返回异常");
      }

      const data = (await response.json()) as ActivitiesResponse;
      const selectedId = data.items[0]?.id ?? null;

      set({ data, loading: false, selectedId });
    } catch (error) {
      set({
        loading: false,
        error: error instanceof Error ? error.message : "抓取失败",
      });
    }
  },
  selectActivity: (id) => set({ selectedId: id }),
}));
