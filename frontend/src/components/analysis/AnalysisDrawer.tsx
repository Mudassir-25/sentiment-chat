import { AnimatePresence, motion } from "motion/react";
import { X } from "lucide-react";
import { useEffect, useRef } from "react";
import { FALLBACK_REASON, INTENT_LABEL, SENTIMENT_LABEL } from "../../lib/labels";
import { spring } from "../../lib/motion";
import type { Analysis, ChatResponse } from "../../types";

interface Props { open: boolean; analysis: Analysis | null; response: ChatResponse | null; onClose: () => void }

const pct = (n: number) => `${Math.round(n * 100)}%`;

export function AnalysisDrawer({ open, analysis: a, response, onClose }: Props) {
  const closeRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!open) return;
    closeRef.current?.focus();
    const on = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", on);
    return () => window.removeEventListener("keydown", on);
  }, [open, onClose]);

  return (
    <AnimatePresence>
      {open && a && (
        <motion.aside className="drawer glass elevated" role="complementary" aria-label="Message analysis"
          initial={{ opacity: 0, x: 18, scale: 0.985 }} animate={{ opacity: 1, x: 0, scale: 1 }} exit={{ opacity: 0, x: 18, scale: 0.985 }} transition={spring.soft}>
          <div className="drawer-head">
            <h2>Analysis</h2>
            <button ref={closeRef} className="icon-btn small" onClick={onClose} aria-label="Close analysis"><X size={15} /></button>
          </div>

          <div className={`result ${a.sentiment.label}`}>
            <span className="eyebrow">Sentiment</span>
            <p className="big" data-testid="drawer-sentiment">{SENTIMENT_LABEL[a.sentiment.label]}{a.sentiment.mixed ? " (mixed)" : ""}</p>
            <p className="small">Confidence estimate {pct(a.sentiment.confidence)}, not a guaranteed probability.</p>
          </div>
          {a.sentiment.uncertain && <p className="uncertain" role="note">Uncertain: {a.sentiment.uncertainty_reasons.join("; ")}.</p>}

          <section>
            <span className="eyebrow">Intent</span>
            <p>{INTENT_LABEL[a.intent.intent] ?? a.intent.intent}{a.intent.ambiguous ? " (ambiguous)" : ""}</p>
            {a.intent.secondary.length > 0 && <p className="muted">Also possible: {a.intent.secondary.map((s) => INTENT_LABEL[s] ?? s).join(", ")}</p>}
          </section>

          <section>
            <span className="eyebrow">Topics</span>
            {a.topics.length ? (
              <ul className="tags">{a.topics.map((t) => <li key={t.phrase}>{t.phrase}{t.from_context ? " · from earlier" : ""}</li>)}</ul>
            ) : <p className="muted">No topic phrases found.</p>}
            <p className="small">Lexical heuristics, not semantic understanding.</p>
          </section>

          {a.context && (
            <section>
              <span className="eyebrow">Context</span>
              <p>{a.context.is_followup ? "Continues the earlier conversation" : "Starts a new subject"}{a.context.sentiment_shift ? " · sentiment shifted" : ""}</p>
            </section>
          )}

          <details className="details">
            <summary><span className="eyebrow">Evidence, kept separate</span></summary>
            <p className="small" style={{ marginTop: 8 }}>{a.sentiment.explanation}</p>
            <div className="two-col">
              <div>
                <h4>Classifier</h4>
                {a.sentiment.classifier ? (<>
                  <p>{SENTIMENT_LABEL[a.sentiment.classifier.label]}</p>
                  <ul className="plain">{a.sentiment.classifier.top_features.map((f) => <li key={f.feature}>“{f.feature}”</li>)}</ul>
                </>) : <p className="muted">Not active (rules fallback).</p>}
              </div>
              <div>
                <h4>Rule layer</h4>
                <p>{SENTIMENT_LABEL[a.sentiment.rules.label]}</p>
                <ul className="plain">
                  {a.sentiment.rules.cues.slice(0, 5).map((c, i) => (
                    <li key={i} className={c.polarity}>“{c.text}” {c.polarity === "positive" ? "+" : "−"}{c.negated ? " (negated)" : ""}</li>
                  ))}
                  {a.sentiment.rules.cues.length === 0 && <li>No lexicon cues</li>}
                </ul>
              </div>
            </div>
          </details>

          <section>
            <span className="eyebrow">Engine &amp; reply</span>
            <p>{a.sentiment.engine.name}</p>
            {response && <p className="muted">Reply generated {response.reply_source === "llm" ? `by AI (${response.provider})` : "locally"}.
              {response.fallback.used ? ` Fallback: ${FALLBACK_REASON[response.fallback.reason ?? ""] ?? response.fallback.detail}.` : ""}</p>}
          </section>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}
