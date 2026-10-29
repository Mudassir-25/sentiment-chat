import { AnimatePresence, motion } from "motion/react";
import { AlertTriangle, RefreshCw, ServerOff, X } from "lucide-react";
import { useEffect, useRef } from "react";
import { START_BACKEND_HINT } from "../../lib/api";
import { FALLBACK_REASON } from "../../lib/labels";
import { dur, ease } from "../../lib/motion";
import type { ChatMessage } from "../../types";
import { MessageBubble } from "./MessageBubble";

const SUGGESTIONS = ["I finally passed my exam!", "The movie was not bad.", "I'm happy about my result, but nervous about tomorrow."];

interface Props {
  messages: ChatMessage[]; pending: boolean; error: { message: string; offline: boolean } | null; backendOffline: boolean;
  selectedId: string | null; onInspect: (m: ChatMessage) => void; onSuggest: (t: string) => void; onRetryBackend: () => void; onDismissError: () => void;
}

export function ChatPanel(p: Props) {
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (p.messages.length || p.pending) end.current?.scrollIntoView?.({ behavior: "smooth", block: "end" });
  }, [p.messages.length, p.pending]);
  const last = p.messages[p.messages.length - 1];
  const fb = last?.response?.fallback;

  return (
    <section className="chat" aria-label="Conversation">
      <div className="column">
        {p.backendOffline && (
          <div className="notice notice-error" role="alert">
            <ServerOff size={17} aria-hidden />
            <div>
              <strong>Backend not reachable.</strong>
              <p>Start it with <code>{START_BACKEND_HINT}</code>, then retry.</p>
            </div>
            <button className="btn" onClick={p.onRetryBackend}><RefreshCw size={13} aria-hidden /> Retry</button>
          </div>
        )}
        <AnimatePresence mode="wait" initial={false}>
          {p.messages.length === 0 && (
            <motion.div key="welcome" className="welcome" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6, transition: { duration: dur.fast } }} transition={{ duration: dur.slow, ease }}>
              <div className="mark big" aria-hidden />
              <h2>Say something. I'll read the room.</h2>
              <p>Sentiment, intent and topics are analysed by the app backend. No account or provider API key is needed.</p>
              <div className="suggestions">
                {SUGGESTIONS.map((s) => <button key={s} className="suggestion" onClick={() => p.onSuggest(s)} disabled={p.backendOffline}>{s}</button>)}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
        {p.messages.length > 0 && (
          <ul className="messages" aria-live="polite" aria-label="Messages">
            {p.messages.map((m) => <MessageBubble key={m.id} m={m} selected={m.id === p.selectedId} onInspect={p.onInspect} />)}
            <AnimatePresence>
              {p.pending && (
                <motion.li key="typing" className="row bot" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: dur.base }}>
                  <div className="typing" role="status" aria-label="Analysing and replying"><i /><i /><i /></div>
                </motion.li>
              )}
            </AnimatePresence>
          </ul>
        )}
        {fb?.used && (
          <div className="notice notice-warn" role="status" style={{ marginTop: 12 }}>
            <AlertTriangle size={15} aria-hidden />
            <span>Used local reply instead of AI: {FALLBACK_REASON[fb.reason ?? ""] ?? fb.detail ?? "AI unavailable"}.</span>
          </div>
        )}
        {p.error && (
          <div className="notice notice-error" role="alert" style={{ marginTop: 12 }}>
            <AlertTriangle size={15} aria-hidden />
            <span>{p.error.offline ? "Couldn't reach the backend. Your message wasn't sent." : p.error.message}</span>
            <button className="icon-btn small" onClick={p.onDismissError} aria-label="Dismiss error"><X size={14} /></button>
          </div>
        )}
        <div ref={end} />
      </div>
    </section>
  );
}
