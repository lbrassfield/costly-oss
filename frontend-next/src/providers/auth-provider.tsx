"use client";

import { createContext, useContext, useState, useCallback, ReactNode } from "react";

interface User {
  user_id: string;
  name: string;
  email: string;
  role?: string;
}

interface AuthContextType {
  user: User | null;
  isDemo: boolean;
  login: (token: string, refreshToken: string, userData: User) => void;
  logout: () => void;
  enterDemo: () => void;
  exitDemo: () => void;
}

const DEMO_USER: User = {
  user_id: "demo",
  name: "Demo User",
  email: "demo@costly.dev",
};

const AuthContext = createContext<AuthContextType>({
  user: null,
  isDemo: false,
  login: () => {},
  logout: () => {},
  enterDemo: () => {},
  exitDemo: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    if (typeof window === "undefined") return null;
    try {
      if (localStorage.getItem("costly_demo") === "1") {
        return DEMO_USER;
      }
      const stored = localStorage.getItem("costly_user");
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });

  const [isDemo, setIsDemo] = useState(() => {
    if (typeof window === "undefined") return false;
    return localStorage.getItem("costly_demo") === "1";
  });

  const login = useCallback(
    (token: string, refreshToken: string, userData: User) => {
      // Clear demo mode on real login
      localStorage.removeItem("costly_demo");
      localStorage.setItem("costly_token", token);
      localStorage.setItem("costly_refresh_token", refreshToken);
      localStorage.setItem("costly_user", JSON.stringify(userData));
      setIsDemo(false);
      setUser(userData);
    },
    []
  );

  const logout = useCallback(() => {
    localStorage.removeItem("costly_token");
    localStorage.removeItem("costly_refresh_token");
    localStorage.removeItem("costly_user");
    localStorage.removeItem("costly_demo");
    setIsDemo(false);
    setUser(null);
  }, []);

  const enterDemo = useCallback(() => {
    localStorage.setItem("costly_demo", "1");
    localStorage.removeItem("costly_token");
    localStorage.removeItem("costly_refresh_token");
    localStorage.removeItem("costly_user");
    setIsDemo(true);
    setUser(DEMO_USER);
  }, []);

  const exitDemo = useCallback(() => {
    localStorage.removeItem("costly_demo");
    setIsDemo(false);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, isDemo, login, logout, enterDemo, exitDemo }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
