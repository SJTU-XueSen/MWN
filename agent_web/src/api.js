// API 封装 — session cookie 认证（同源; dev 由 vite 代理到 :5021）
export async function api(url, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  const resp = await fetch(url, { ...options, headers, credentials: 'include' });
  if (resp.status === 401) {
    return { status: 401, error: 'not_logged_in', detail: '请先登录' };
  }
  const text = await resp.text();
  try {
    return { status: resp.status, ...(text ? JSON.parse(text) : {}) };
  } catch {
    return { status: resp.status, raw: text };
  }
}
