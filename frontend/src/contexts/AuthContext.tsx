import { createContext, useContext, useState, useEffect, useRef, type ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { authStore } from "@/lib/authStore";
import { fetchMe, restoreSession, logout as apiLogout } from "@/api/auth";
import type { AppUser } from "@/types/user";

interface AuthContextValue {
  user: AppUser | null;
  loading: boolean;
  setUser: (user: AppUser | null) => void;
  logout: () => void;
  reload: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  loading: true,
  setUser: () => {},
  logout: () => {},
  reload: async () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const prevIdRef = useRef<number | null>(null);
  const [user, setUserState] = useState<AppUser | null>(null);
  const [loading, setLoading] = useState(true);

  // Every identity transition passes through here — login, logout, session
  // expiry, account switch. Drop the previous user's cached queries on any
  // id change so the next user can never be served stale PHI.
  const setUser = (next: AppUser | null) => {
    const newId = next?.id ?? null;
    if (prevIdRef.current !== null && prevIdRef.current !== newId) {
      queryClient.clear();
    }
    prevIdRef.current = newId;
    setUserState(next);
  };

  const loadUser = async () => {
    try {
      setUser(await fetchMe());
    } catch {
      setUser(null);
    }
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const restored = await restoreSession();
      if (cancelled) return;
      if (restored) await loadUser();
      setLoading(false);
    })();

    // Cross-instance reactivity: token cleared elsewhere → drop the user.
    const unsubscribe = authStore.subscribe(() => {
      if (!authStore.getRefreshToken()) setUser(null);
    });
    return () => {
      cancelled = true;
      unsubscribe();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const logout = async () => {
    await apiLogout();
    setUser(null);
  };

  return (
    <AuthContext value={{ user, loading, setUser, logout, reload: loadUser }}>
      {children}
    </AuthContext>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  return useContext(AuthContext);
}
