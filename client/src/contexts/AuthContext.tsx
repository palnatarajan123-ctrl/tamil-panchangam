// client/src/contexts/AuthContext.tsx
import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { apiRequest } from "@/lib/queryClient";
import { setTokens, clearTokens, getAccessToken } from "@/lib/auth";

interface User {
  id: string;
  email: string;
  name: string;
  role: string;
}

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  googleLogin: (idToken: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Verify token on mount
  useEffect(() => {
    if (!getAccessToken()) {
      setIsLoading(false);
      return;
    }
    apiRequest("GET", "/api/auth/me")
      .then((r) => r.json())
      .then((data) => setUser(data.user ?? null))
      .catch(() => {
        clearTokens();
        setUser(null);
      })
      .finally(() => setIsLoading(false));
  }, []);

  async function login(email: string, password: string) {
    const res = await apiRequest("POST", "/api/auth/login", { email, password });
    const data = await res.json();
    setTokens(data.access_token, data.refresh_token);
    setUser(data.user);
  }

  async function register(email: string, password: string, name: string) {
    const res = await apiRequest("POST", "/api/auth/register", { email, password, name });
    const data = await res.json();
    setTokens(data.access_token, data.refresh_token);
    setUser(data.user);
  }

  async function googleLogin(idToken: string) {
    const res = await apiRequest("POST", "/api/auth/google", { id_token: idToken });
    const data = await res.json();
    setTokens(data.access_token, data.refresh_token);
    setUser(data.user);
  }

  async function logout() {
    try {
      const { getRefreshToken } = await import("@/lib/auth");
      const refresh = getRefreshToken();
      if (refresh) {
        await apiRequest("POST", "/api/auth/logout", { refresh_token: refresh });
      }
    } catch {
      // ignore
    } finally {
      clearTokens();
      setUser(null);
      window.location.href = "/login";
    }
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, googleLogin, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
