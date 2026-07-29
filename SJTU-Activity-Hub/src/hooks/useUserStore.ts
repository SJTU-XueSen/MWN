import { create } from "zustand";

export type UserInfo = {
  nickname: string;
  realName: string;
  contact: string;
};

type UserState = {
  user: UserInfo | null;
  login: (info: UserInfo) => void;
  logout: () => void;
};

const STORAGE_KEY = "compete_user";

function loadUser(): UserInfo | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as UserInfo) : null;
  } catch {
    return null;
  }
}

function saveUser(user: UserInfo) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
}

function clearUser() {
  localStorage.removeItem(STORAGE_KEY);
}

export const useUserStore = create<UserState>((set) => ({
  user: loadUser(),
  login: (info) => {
    saveUser(info);
    set({ user: info });
  },
  logout: () => {
    clearUser();
    set({ user: null });
  },
}));
