import { MotionConfig } from "motion/react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { AnalysisDrawer } from "./components/analysis/AnalysisDrawer";
import { AnalyticsDashboard } from "./components/analytics/AnalyticsDashboard";
import { ChatPanel } from "./components/chat/ChatPanel";
import { Composer } from "./components/chat/Composer";
import { Header } from "./components/layout/Header";
import { SettingsPanel } from "./components/settings/SettingsPanel";
import { useCapabilities } from "./hooks/useCapabilities";
import { useChat } from "./hooks/useChat";
import { useTheme } from "./hooks/useTheme";
import type { ChatMessage, Mode } from "./types";

const MODE_KEY = "sc-mode";
const readMode = (): Mode => {
  try {
    const v = localStorage.getItem(MODE_KEY);
    return v === "local_only" || v === "ai_enhanced" ? v : "automatic";
  } catch { return "automatic"; }
};

type Page = "chat" | "analytics";

export default function App() {
  const theme = useTheme();
  const { caps, offline, refresh } = useCapabilities();
  const [mode, setModeState] = useState<Mode>(readMode);
  const [provider, setProvider] = useState<string | null>(null);
  const [page, setPage] = useState<Page>("chat");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [inspectedId, setInspectedId] = useState<string | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const chat = useChat(mode, provider);

  const setMode = useCallback((m: Mode) => {
    setModeState(m);
    try { localStorage.setItem(MODE_KEY, m); } catch { /* ignore */ }
  }, []);

  useEffect(() => { if (caps && !provider) setProvider(caps.default_provider); }, [caps, provider]);
  const hasProvider = !!caps?.providers.some((p) => p.configured);
  const effectiveAI = hasProvider && mode !== "local_only";

  const inspected = useMemo(() => {
    const m = chat.messages.find((x) => x.id === inspectedId);
    if (!m) return null;
    return m.role === "user"
      ? { analysis: m.analysisFor ?? null, response: chat.messages[chat.messages.indexOf(m) + 1]?.response ?? null }
      : { analysis: m.response?.analysis ?? null, response: m.response ?? null };
  }, [chat.messages, inspectedId]);

  const inspect = useCallback((m: ChatMessage) => { setInspectedId(m.id); setDrawerOpen(true); }, []);
  const closeDrawer = useCallback(() => setDrawerOpen(false), []);
  const clear = async () => { await chat.reset(); setInspectedId(null); setDrawerOpen(false); setSettingsOpen(false); };

  return (
    <MotionConfig reducedMotion="user">
      <div className="app">
        <div className={`shell glass ${drawerOpen ? "has-drawer" : ""}`}>
          <Header caps={caps} mode={mode} page={page} effectiveAI={effectiveAI} resolvedTheme={theme.resolved}
            onNavigate={setPage} onToggleTheme={theme.toggle} onOpenSettings={() => setSettingsOpen(true)} />
          <main className={`stage ${drawerOpen ? "drawer-open" : ""}`}>
            {page === "analytics" ? (
              <AnalyticsDashboard />
            ) : (
              <div className="pane">
                <ChatPanel messages={chat.messages} pending={chat.pending} error={chat.error} backendOffline={offline}
                  selectedId={drawerOpen ? inspectedId : null} onInspect={inspect} onSuggest={(t) => void chat.send(t)} onRetryBackend={() => void refresh()}
                  onDismissError={chat.dismissError} />
                <div className="dock">
                  <Composer onSend={chat.send} disabled={chat.pending || offline} pending={chat.pending} offline={offline} max={caps?.max_message_chars ?? 1000} />
                </div>
              </div>
            )}
            <AnalysisDrawer open={drawerOpen} analysis={inspected?.analysis ?? null} response={inspected?.response ?? null} onClose={closeDrawer} />
          </main>
        </div>
        <SettingsPanel open={settingsOpen} caps={caps} mode={mode} provider={provider} themePref={theme.pref} effectiveAI={effectiveAI}
          onMode={setMode} onProvider={setProvider} onTheme={theme.setPref} onClear={() => void clear()}
          onClose={() => setSettingsOpen(false)} onRefreshCaps={() => void refresh()} />
      </div>
    </MotionConfig>
  );
}
