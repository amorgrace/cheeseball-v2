// admin-ui/src/lib/api.ts
const DEFAULT_API_URL = process.env.NODE_ENV === "production" ? "https://cheeseball-v2.vercel.app/api" : "http://localhost:8000/api";

export function getApiUrl(): string {
  if (typeof window !== "undefined") {
    // Client-side environment
    return window.localStorage.getItem("API_URL") || process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_URL;
  }
  return process.env.NEXT_PUBLIC_API_URL || DEFAULT_API_URL;
}


export function setCustomApiUrl(url: string) {
  if (typeof window !== "undefined") {
    window.localStorage.setItem("API_URL", url);
  }
}

export function getAuthToken(): string | null {
  if (typeof window !== "undefined") {
    return window.localStorage.getItem("admin_token");
  }
  return null;
}

export function setAuthToken(token: string | null) {
  if (typeof window !== "undefined") {
    if (token) {
      window.localStorage.setItem("admin_token", token);
      document.cookie = `access_token=${token}; path=/; max-age=86400; SameSite=Lax`;
    } else {
      window.localStorage.removeItem("admin_token");
      document.cookie = "access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
    }
  }
}

import { getAccessToken, refreshAccessToken, clearTokens } from "./tokenStore";

export interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined>;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const baseUrl = getApiUrl();
  const url = (() => {
    let u = `${baseUrl}${path}`;
    if (options.params) {
      const sp = new URLSearchParams();
      Object.entries(options.params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== "") {
          sp.append(k, String(v));
        }
      });
      const qs = sp.toString();
      if (qs) u += `?${qs}`;
    }
    return u;
  })();

  const token = getAccessToken();
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(url, { ...options, headers });

  if (response.status === 401 && !path.includes("/auth/token/pair")) {
    try {
      await refreshAccessToken();
      const newToken = getAccessToken();
      if (newToken) {
        headers.set("Authorization", `Bearer ${newToken}`);
      }
      const retry = await fetch(url, { ...options, headers });
      if (!retry.ok) {
        throw new Error("Unauthorized after token refresh");
      }
      return (await retry.json()) as T;
    } catch (e) {
      clearTokens();
      if (typeof window !== "undefined" && !window.location.pathname.startsWith("/login")) {
        window.location.href = `/login?expired=true&redirect=${encodeURIComponent(window.location.pathname)}`;
      }
      throw new Error("Unauthorized");
    }
  }

  if (!response.ok) {
    let errorDetail = "An error occurred";
    try {
      const data = await response.json();
      errorDetail = data.detail || JSON.stringify(data) || errorDetail;
    } catch {
      errorDetail = response.statusText || errorDetail;
    }
    throw new Error(errorDetail);
  }

  if (response.status === 204) {
    return {} as T;
  }

  try {
    return (await response.json()) as T;
  } catch {
    return {} as T;
  }
}

export const api = {
  get: <T>(path: string, params?: Record<string, any>, options?: RequestOptions) => request<T>(path, { method: "GET", params, ...options }),
  post: <T>(path: string, body?: any, options?: RequestOptions) =>
    request<T>(path, {
      method: "POST",
      body: body instanceof FormData ? body : JSON.stringify(body),
      ...options,
    }),
  patch: <T>(path: string, body?: any, options?: RequestOptions) =>
    request<T>(path, {
      method: "PATCH",
      body: body instanceof FormData ? body : JSON.stringify(body),
      ...options,
    }),
  delete: <T>(path: string, options?: RequestOptions) => request<T>(path, { method: "DELETE", ...options }),
};
