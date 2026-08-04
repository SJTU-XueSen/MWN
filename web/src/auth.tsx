import { createContext, useContext, useEffect, useState, ReactNode } from "react";

export interface User {
  id: number;
  username: string;
  real_name?: string;
  email?: string;
}

interface AuthState {
  user: User | null;
  ready: boolean;
  login: (u: User) => void;
  logout: () => void;
}

const AuthCtx = createContext<AuthState>({
  user: null,
  ready: false,
  login: () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    fetch("/api/auth/me", { credentials: "include" })
      .then((r) => (r.ok ? r.json() : Promise.resolve(null)))
      .then((u) => setUser(u))
      .catch(() => setUser(null))
      .finally(() => setReady(true));
  }, []);

  const login = (u: User) => setUser(u);
  const logout = () => setUser(null);

  return <AuthCtx.Provider value={{ user, ready, login, logout }}>{children}</AuthCtx.Provider>;
}

export function useAuth() {
  return useContext(AuthCtx);
}

/** 统一 API 请求（自动携带 cookie） */
export async function api<T = any>(url: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(url, {
    credentials: "include",
    headers: init?.body ? { "Content-Type": "application/json" } : undefined,
    ...init,
  });
  if (resp.status === 401) {
    // 全局处理：未登录 → 跳转登录页
    if (!window.location.pathname.startsWith("/login")) {
      window.location.href = "/login";
    }
    throw new Error("not_logged_in");
  }
  return resp.json() as Promise<T>;
}
