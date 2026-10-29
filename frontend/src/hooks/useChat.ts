import { useCallback, useMemo, useRef, useState } from "react";
import { api, ApiError } from "../lib/api";
import type { ChatMessage, Mode } from "../types";

const uid = () => (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(36).slice(2)}`);

export function useChat(mode: Mode, provider: string | null) {
  const sessionId = useRef(`s-${uid()}`.slice(0, 40));
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<{ message: string; offline: boolean } | null>(null);

  const send = useCallback(async (text: string) => {
    const clean = text.trim();
    if (!clean || pending) return false;
    setError(null);
    const userMsg: ChatMessage = { id: uid(), role: "user", text: clean };
    setMessages((m) => [...m, userMsg]);
    setPending(true);
    try {
      const res = await api.chat({ session_id: sessionId.current, message: clean, mode, provider });
      setMessages((m) => [
        ...m.map((x) => (x.id === userMsg.id ? { ...x, analysisFor: res.analysis } : x)),
        { id: uid(), role: "assistant", text: res.reply, response: res },
      ]);
      return true;
    } catch (e) {
      setMessages((m) => m.filter((x) => x.id !== userMsg.id)); // no fake reply; let the user retry
      setError({ message: e instanceof ApiError ? e.message : "Something went wrong.", offline: e instanceof ApiError && e.kind === "offline" });
      return clean;
    } finally {
      setPending(false);
    }
  }, [mode, provider, pending]);

  const reset = useCallback(async () => {
    try { await api.clearSession(sessionId.current); } catch { /* backend may be down; local state is cleared anyway */ }
    sessionId.current = `s-${uid()}`.slice(0, 40);
    setMessages([]);
    setError(null);
  }, []);

  const lastAnalysis = useMemo(() => [...messages].reverse().find((m) => m.response)?.response ?? null, [messages]);
  return { messages, pending, error, send, reset, dismissError: () => setError(null), lastAnalysis };
}
