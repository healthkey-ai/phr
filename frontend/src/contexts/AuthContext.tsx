import { createContext, ReactNode, useContext, useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api";
import { authStore } from "@/lib/auth";
import type { User } from "@/types";

interface AuthContextValue {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string) => Promise<void>;
  signOut: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

async function fetchMe(): Promise<User | null> {
  if (!authStore.isAuthenticated()) return null;
  try {
    const r = await api.get<User>("/auth/me/");
    return r.data;
  } catch {
    authStore.clear();
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [authVersion, setAuthVersion] = useState(0);

  // Re-fetch when token changes
  useEffect(() => {
    const unsub = authStore.subscribe(() => setAuthVersion((v) => v + 1));
    return () => {
      unsub();
    };
  }, []);

  const { data: user = null, isLoading } = useQuery({
    queryKey: ["auth", "me", authVersion],
    queryFn: fetchMe,
  });

  const signIn = async (email: string, password: string) => {
    const r = await api.post("/auth/login/", { email, password });
    authStore.setTokens({ access: r.data.access, refresh: r.data.refresh });
    queryClient.invalidateQueries({ queryKey: ["auth"] });
  };

  const signUp = async (email: string, password: string) => {
    const r = await api.post("/auth/register/", { email, password });
    authStore.setTokens({ access: r.data.tokens.access, refresh: r.data.tokens.refresh });
    queryClient.invalidateQueries({ queryKey: ["auth"] });
  };

  const signOut = () => {
    authStore.clear();
    queryClient.clear();
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: Boolean(user),
        isLoading,
        signIn,
        signUp,
        signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
