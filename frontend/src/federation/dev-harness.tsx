import { StrictMode, useCallback, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient } from "@tanstack/react-query";
import axios, { type AxiosInstance } from "axios";

import { LabUploads } from "./LabUploads";
import { LabResults } from "./LabResults";
import "./labs.css";

const API_BASE = "http://localhost:9000/api/v1";

function loadTokens(): { access: string; refresh: string } | null {
  const raw = localStorage.getItem("dev_phr_tokens");
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    if (parsed.access && parsed.refresh) return parsed;
  } catch {}
  return null;
}

function saveTokens(tokens: { access: string; refresh: string }) {
  localStorage.setItem("dev_phr_tokens", JSON.stringify(tokens));
}

function clearTokens() {
  localStorage.removeItem("dev_phr_tokens");
  localStorage.removeItem("dev_phr_token");
}

function createApiClient(
  tokens: { access: string; refresh: string },
  onSessionExpired: () => void,
): AxiosInstance {
  const client = axios.create({
    baseURL: API_BASE,
    headers: { Authorization: `Bearer ${tokens.access}` },
  });

  client.interceptors.response.use(
    (res) => res,
    async (err) => {
      if (err.response?.status === 401 && !err.config._retry) {
        err.config._retry = true;
        try {
          const refreshRes = await axios.post(`${API_BASE}/auth/token/refresh/`, {
            refresh: tokens.refresh,
          });
          tokens.access = refreshRes.data.access;
          saveTokens(tokens);
          err.config.headers.Authorization = `Bearer ${tokens.access}`;
          return client.request(err.config);
        } catch {
          onSessionExpired();
        }
      }
      return Promise.reject(err);
    },
  );

  return client;
}

function App() {
  const [tokens, setTokens] = useState(loadTokens);
  const [events, setEvents] = useState<string[]>([]);
  const queryClientRef = useRef(new QueryClient({ defaultOptions: { queries: { staleTime: 30_000, retry: 1 } } }));
  const inputRef = useRef<HTMLInputElement>(null);

  const handleSessionExpired = useCallback(() => {
    clearTokens();
    setTokens(null);
  }, []);

  const logEvent = useCallback((name: string, data?: unknown) => {
    const entry = data
      ? `${name}: ${JSON.stringify(data).slice(0, 100)}`
      : name;
    setEvents((prev) => [entry, ...prev].slice(0, 50));
  }, []);

  const apiClient = useMemo(() => {
    if (!tokens) return null;
    return createApiClient(tokens, handleSessionExpired);
  }, [tokens, handleSessionExpired]);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    const form = e.target as HTMLFormElement;
    const email = (form.elements.namedItem("email") as HTMLInputElement).value;
    const password = (form.elements.namedItem("password") as HTMLInputElement).value;
    try {
      const res = await axios.post(`${API_BASE}/auth/login/`, { email, password });
      const t = { access: res.data.access, refresh: res.data.refresh };
      saveTokens(t);
      setTokens(t);
    } catch {
      alert("Login failed — check credentials and that Django is running on :9000");
    }
  };

  if (!tokens || !apiClient) {
    return (
      <div style={{ padding: 40, maxWidth: 400, margin: "0 auto", fontFamily: "sans-serif" }}>
        <h1>Dev Harness — Login</h1>
        <p style={{ color: "#666", fontSize: 14 }}>
          Login with your PHR dev credentials to get a JWT.
        </p>
        <form onSubmit={handleLogin} style={{ marginTop: 16 }}>
          <input name="email" placeholder="email" style={{ display: "block", width: "100%", padding: 8, marginBottom: 8 }} />
          <input name="password" type="password" placeholder="password" style={{ display: "block", width: "100%", padding: 8, marginBottom: 8 }} />
          <button type="submit" style={{ padding: "8px 16px" }}>Login</button>
        </form>
        <hr style={{ margin: "24px 0" }} />
        <p style={{ color: "#666", fontSize: 14 }}>
          Or paste access + refresh tokens (JSON):
        </p>
        <input
          ref={inputRef}
          placeholder='{"access":"...","refresh":"..."}'
          style={{ display: "block", width: "100%", padding: 8, marginBottom: 8 }}
        />
        <button
          onClick={() => {
            try {
              const parsed = JSON.parse(inputRef.current?.value || "");
              if (parsed.access && parsed.refresh) {
                saveTokens(parsed);
                setTokens(parsed);
              }
            } catch {
              alert("Paste valid JSON: {\"access\":\"...\",\"refresh\":\"...\"}");
            }
          }}
          style={{ padding: "8px 16px" }}
        >
          Use tokens
        </button>
      </div>
    );
  }

  return (
    <div style={{ padding: 24, maxWidth: 900, margin: "0 auto" }}>
      <header style={{ marginBottom: 24, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1 style={{ fontSize: 20, fontWeight: 700 }}>Labs Federation — Dev Harness</h1>
        <button
          onClick={() => { clearTokens(); setTokens(null); }}
          style={{ padding: "4px 12px", fontSize: 12 }}
        >
          Logout
        </button>
      </header>

      <section style={{ marginBottom: 32 }}>
        <LabUploads
          apiClient={apiClient}
          queryClient={queryClientRef.current}
          onUploadComplete={(upload) => logEvent("onUploadComplete", { id: upload.id, status: upload.status })}
          onResultsSaved={(res) => logEvent("onResultsSaved", { saved: res.saved_count })}
        />
      </section>

      <hr style={{ margin: "24px 0" }} />

      <section style={{ marginBottom: 32 }}>
        <LabResults
          apiClient={apiClient}
          queryClient={queryClientRef.current}
          onResultDeleted={(id) => logEvent("onResultDeleted", { id })}
        />
      </section>

      <hr style={{ margin: "24px 0" }} />

      <section>
        <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 8 }}>Event Log</h2>
        <div
          data-testid="event-log"
          style={{
            background: "#f9fafb",
            border: "1px solid #e5e7eb",
            borderRadius: 6,
            padding: 12,
            maxHeight: 200,
            overflowY: "auto",
            fontSize: 12,
            fontFamily: "monospace",
          }}
        >
          {events.length === 0 ? (
            <span style={{ color: "#9ca3af" }}>No events yet — interact with the components above</span>
          ) : (
            events.map((ev, i) => <div key={i}>{ev}</div>)
          )}
        </div>
      </section>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
