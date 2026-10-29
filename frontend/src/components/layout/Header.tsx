import { AnimatePresence, motion } from "motion/react";
import { Moon, Settings, Sun } from "lucide-react";
import { MODE_LABEL } from "../../lib/labels";
import { dur, ease } from "../../lib/motion";
import type { Capabilities, Mode } from "../../types";

interface Props {
  caps: Capabilities | null; mode: Mode; page: "chat" | "analytics"; effectiveAI: boolean; resolvedTheme: "light" | "dark";
  onNavigate: (page: "chat" | "analytics") => void; onToggleTheme: () => void; onOpenSettings: () => void;
}

export function Header({ caps, mode, page, effectiveAI, resolvedTheme, onNavigate, onToggleTheme, onOpenSettings }: Props) {
  const engine = caps?.engine;
  const modeText = !caps ? "Backend offline" : mode === "local_only" ? "Local NLP" : effectiveAI ? "AI enhanced" : "Local NLP";
  const next = resolvedTheme === "dark" ? "Pearl (light)" : "Midnight (dark)";
  return (
    <header className="header">
      <div className="brand">
        <div className="mark" aria-hidden />
        <div>
          <h1>Sentiment Chat</h1>
          <p className="tagline">Local-first sentiment, thoughtful replies</p>
        </div>
      </div>
      <div className="header-actions">
        <nav className="main-nav" aria-label="Main navigation">
          <button type="button" className={`nav-button ${page === "chat" ? "active" : ""}`} onClick={() => onNavigate("chat")}>Chat</button>
          <button type="button" className={`nav-button ${page === "analytics" ? "active" : ""}`} onClick={() => onNavigate("analytics")}>Analytics</button>
        </nav>
        <span className={`mode-pill ${caps ? (modeText === "AI enhanced" ? "ai" : "local") : "off"}`} role="status"
              aria-label={`Active mode: ${modeText}`} title={engine?.note}>
          <span className="pulse" aria-hidden /> {modeText}
          {engine && <span className="engine"> · {engine.id === "rules-fallback" ? "rules fallback" : "TF-IDF + LogReg"}</span>}
        </span>
        <button className="icon-btn" onClick={onToggleTheme} aria-label={`Switch to ${next} theme`}>
          <AnimatePresence mode="wait" initial={false}>
            <motion.span key={resolvedTheme} className="theme-icon" initial={{ opacity: 0, rotate: -50, scale: 0.7 }} animate={{ opacity: 1, rotate: 0, scale: 1 }}
              exit={{ opacity: 0, rotate: 50, scale: 0.7 }} transition={{ duration: dur.fast, ease }}>
              {resolvedTheme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
            </motion.span>
          </AnimatePresence>
        </button>
        <button className="icon-btn gear" onClick={onOpenSettings} aria-label="Open settings" title={`Mode: ${MODE_LABEL[mode]}`}>
          <Settings size={17} />
        </button>
      </div>
    </header>
  );
}
