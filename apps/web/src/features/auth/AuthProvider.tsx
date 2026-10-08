import {
  createContext,
  useCallback,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { z } from "zod";
import { api, ApiError } from "../../lib/api";
import { session, type Session } from "../../lib/schemas";
export const AuthContext = createContext<{
  identity: Session | null;
  loading: boolean;
  error: string;
  reload: () => Promise<void>;
  logout: () => Promise<void>;
} | null>(null);
export function AuthProvider({ children }: { children: ReactNode }) {
  const [identity, setIdentity] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const reload = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setIdentity(await api("/auth/me", session));
    } catch (e) {
      setIdentity(null);
      if (!(e instanceof ApiError && e.status === 401))
        setError(e instanceof Error ? e.message : "Could not load session");
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    void reload();
  }, [reload]);
  async function logout() {
    if (!identity) return;
    try {
      await api(
        "/auth/logout",
        z.undefined(),
        { method: "POST", body: "{}" },
        identity.csrf_token,
      );
      setIdentity(null);
      window.location.assign("/login");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not sign out");
    }
  }
  return (
    <AuthContext.Provider value={{ identity, loading, error, reload, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
