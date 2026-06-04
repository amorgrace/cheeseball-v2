// auth.tsx – Auth context with in‑memory token store
"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { setTokens, clearTokens, getAccessToken, refreshAccessToken } from "../lib/tokenStore";
import { api } from "./api";

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  phone_number: string | null;
  referral_code: string;
  is_staff: boolean;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  const fetchUser = async () => {
    try {
      const data = await api.get<User>("/auth/me");
      if (data.is_staff) {
        setUser(data);
      } else {
        clearTokens();
        setUser(null);
        router.push(`/login?redirect=${encodeURIComponent(pathname)}`);
      }
    } catch (err) {
      console.error("Failed to fetch current user profile:", err);
      clearTokens();
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
  if (getAccessToken()) {
    fetchUser();
  } else {
    setLoading(false);
  }
}, []);

  useEffect(() => {
    if (!loading) {
      const isLoginPage = pathname === "/login";
      if (!user && !isLoginPage) {
        router.push(`/login?redirect=${encodeURIComponent(pathname)}`);
      } else if (user && isLoginPage) {
        const params = new URLSearchParams(window.location.search);
        router.push(params.get("redirect") || "/");
      }
    }
  }, [user, loading, pathname]);

  const login = async (email: string, password: string) => {
    try {
      const data = await api.post<{ access: string; refresh: string }>("/auth/token/pair", {
        email,
        password,
      });
      if (data.access && data.refresh) {
        setTokens(data.access, data.refresh);
        const profile = await api.get<User>("/auth/me");
        if (profile.is_staff) {
          setUser(profile);
          const params = new URLSearchParams(window.location.search);
          router.push(params.get("redirect") || "/");
        } else {
          clearTokens();
          setUser(null);
          throw new Error("Access denied. Admin permissions required.");
        }
      } else {
        throw new Error("Invalid authentication response.");
      }
    } catch (err: any) {
      throw err;
    }
  };

  const logout = () => {
    clearTokens();
    setUser(null);
    router.push("/login");
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, refreshUser: fetchUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
