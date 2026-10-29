import { AnimatePresence, motion } from "motion/react";
import { CheckCircle2, Loader2, Trash2, X, XCircle } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api } from "../../lib/api";
import { MODE_HELP, MODE_LABEL } from "../../lib/labels";
import { dur, ease, spring } from "../../lib/motion";
import type { ThemePref } from "../../hooks/useTheme";
import type { Capabilities, Mode, ProviderStatus } from "../../types";

interface Props {
  open: boolean; caps: Capabilities | null; mode: Mode; provider: string | null; themePref: ThemePref; effectiveAI: boolean;
  onMode: (m: Mode) => void; onProvider: (p: string | null) => void; onTheme: (t: ThemePref) => void;
  onClear: () => void; onClose: () => void; onRefreshCaps: () => void;
}
const MODES: Mode[] = ["automatic", "local_only", "ai_enhanced"];
const THEMES: { v: ThemePref; l: string }[] = [{ v: "system", l: "System" }, { v: "light", l: "Pearl" }, { v: "dark", l: "Midnight" }];
const CONN = { untested: "Not tested yet", ok: "Connection OK", failed: "Last test failed" } as const;

export function SettingsPanel(p: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState<ProviderStatus | null>(null);
  useEffect(() => {
    if (!p.open) return;
    ref.current?.querySelector<HTMLElement>("input,button")?.focus();
    const on = (e: KeyboardEvent) => e.key === "Escape" && p.onClose();
    window.addEventListener("keydown", on);
    return () => window.removeEventListener("keydown", on);
  }, [p.open]); // eslint-disable-line react-hooks/exhaustive-deps

  const providers = p.caps?.providers ?? [];
  const configured = providers.filter((x) => x.configured);
  const active = providers.find((x) => x.id === p.provider) ??
    providers.find((x) => x.id === p.caps?.default_provider) ?? null;
  const shown = result && result.id === active?.id ? result : active;

  async function test() {
    if (!active) return;
    setTesting(true);
    try { setResult(await api.testProvider(active.id)); p.onRefreshCaps(); } catch { setResult({ ...active, connection: "failed", last_error: "Could not reach the backend." }); }
    finally { setTesting(false); }
  }

  return (
    <AnimatePresence>
      {p.open && (
        <motion.div className="overlay" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: dur.base, ease }} onClick={p.onClose}>
          <motion.div ref={ref} className="modal glass elevated" role="dialog" aria-modal="true" aria-label="Settings"
            initial={{ opacity: 0, y: 14, scale: 0.985 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 10, scale: 0.99 }} transition={spring.soft}
            onClick={(e) => e.stopPropagation()}>
            <div className="modal-head"><h2>Settings</h2>
              <button className="icon-btn small" onClick={p.onClose} aria-label="Close settings"><X size={15} /></button></div>

            <fieldset>
              <legend>Response mode</legend>
              <div className="group inset">
                {MODES.map((m) => (
                  <label key={m} className={`option ${p.mode === m ? "on" : ""}`}>
                    <input type="radio" name="mode" value={m} checked={p.mode === m} onChange={() => p.onMode(m)} />
                    <span><strong>{MODE_LABEL[m]}</strong><small>{MODE_HELP[m]}</small></span>
                  </label>
                ))}
              </div>
              <div className="status-row inset" aria-label="Current status">
                <div><span>AI provider</span><span>{configured.length ? "Configured" : "Not configured"}</span></div>
                <div><span>Replies right now</span><span>{p.caps ? (p.effectiveAI ? "AI, local on failure" : "Local NLP") : "Backend offline"}</span></div>
              </div>
            </fieldset>

            <fieldset>
              <legend>AI provider</legend>
              {providers.length === 0 ? (
                <p className="small">Provider status is unavailable while the backend is offline.</p>
              ) : (<>
                <label className="field"><span>Provider</span>
                  <select value={p.provider ?? ""} onChange={(e) => p.onProvider(e.target.value || null)}>
                    <option value="">Use server default{p.caps?.default_provider ? ` (${providers.find((x) => x.id === p.caps?.default_provider)?.label})` : " (local only)"}</option>
                    {providers.map((x) => <option key={x.id} value={x.id}>{x.label} · {x.model}{x.configured ? "" : " · not configured"}</option>)}
                  </select></label>
                {!configured.length && <p className="small">No provider configured. Set a backend API key (or Ollama URL) in the Render environment or <code>backend/.env</code>. The app works locally without one. Keys are never entered or stored in the browser.</p>}
                <p className="small">{active?.configured ? `Configured is not the same as working. ${shown?.connection === "untested" ? CONN.untested + "." : ""}` : `${active?.label ?? "AI provider"} is not configured. Choose a configured provider or use local mode.`}</p>
                <div><button className="btn" onClick={test} disabled={testing || !active?.configured}>{testing ? <Loader2 className="spin" size={13} /> : null} Test connection</button></div>
                {shown?.connection === "ok" && <p className="ok"><CheckCircle2 size={14} aria-hidden /> Connection OK</p>}
                {shown?.connection === "failed" && <p className="bad"><XCircle size={14} aria-hidden /> {shown.last_error ?? "Failed"}</p>}
              </>)}
            </fieldset>

            <fieldset>
              <legend>Theme</legend>
              <div className="segmented inset" role="radiogroup" aria-label="Theme">
                {THEMES.map((t) => (
                  <button key={t.v} role="radio" aria-checked={p.themePref === t.v} className={p.themePref === t.v ? "on" : ""} onClick={() => p.onTheme(t.v)}>
                    {p.themePref === t.v && <motion.span layoutId="theme-thumb" className="thumb" transition={spring.snappy} />}
                    <span>{t.l}</span>
                  </button>
                ))}
              </div>
            </fieldset>

            <div>
              <button className="btn danger" onClick={p.onClear}><Trash2 size={13} aria-hidden /> Clear conversation</button>
              <p className="small" style={{ marginTop: 8 }}>Conversations live in memory only and disappear when you clear them or close the tab.</p>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
