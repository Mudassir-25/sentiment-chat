import { Cloud, Cpu, Sparkles } from "lucide-react";
import { SENTIMENT_LABEL } from "../../lib/labels";
import type { Sentiment, SentimentAnalysis } from "../../types";

export function SentimentChip({ s }: { s: SentimentAnalysis }) {
  const label: Sentiment = s.label;
  return (
    <span className={`chip chip-${label}`} data-testid="sentiment-chip">
      <span className="dot" aria-hidden />
      {SENTIMENT_LABEL[label]}
      {s.mixed ? " · mixed" : s.uncertain ? " · uncertain" : ""}
    </span>
  );
}

export function SourceChip({ source, provider }: { source: "local" | "llm"; provider: string | null }) {
  return source === "llm" ? (
    <span className="chip chip-ai"><Sparkles size={12} aria-hidden /> AI{provider ? ` · ${provider}` : ""}</span>
  ) : (
    <span className="chip chip-local"><Cpu size={12} aria-hidden /> Local</span>
  );
}

export function CloudOff() { return <Cloud size={14} aria-hidden />; }
