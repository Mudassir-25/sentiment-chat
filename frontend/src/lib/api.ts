import type { AnalyticsSnapshot, Capabilities, ChatResponse, Mode, ProviderStatus } from "../types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/+$/, "");

export class ApiError extends Error {
  constructor(message: string, public kind: "offline" | "http", public status?: number) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { ...init, headers: { "Content-Type": "application/json", ...init?.headers } });
  } catch {
    throw new ApiError("Cannot reach the backend.", "offline");
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status}).`;
    try {
      const j = await res.json();
      if (typeof j.detail === "string") detail = j.detail;
      else if (Array.isArray(j.detail) && j.detail[0]?.msg) detail = String(j.detail[0].msg);
    } catch { /* keep default */ }
    throw new ApiError(detail, "http", res.status);
  }
  return res.json() as Promise<T>;
}

export const api = {
  capabilities: () => request<Capabilities>("/api/capabilities"),
  analytics: () => request<AnalyticsSnapshot>("/api/analytics"),
  chat: (body: { session_id: string; message: string; mode: Mode; provider?: string | null }) =>
    request<ChatResponse>("/api/chat", { method: "POST", body: JSON.stringify(body) }),
  clearSession: (id: string) => request<{ cleared: boolean }>(`/api/sessions/${id}`, { method: "DELETE" }),
  testProvider: (id: string) => request<ProviderStatus>(`/api/llm/${id}/test`, { method: "POST" }),
};

export const START_BACKEND_HINT = "cd backend && uvicorn app.main:app --port 8000";
