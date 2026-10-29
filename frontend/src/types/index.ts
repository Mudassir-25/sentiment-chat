export type Sentiment = "positive" | "neutral" | "negative";
export type Mode = "automatic" | "local_only" | "ai_enhanced";

export interface Cue { text: string; polarity: "positive" | "negative"; weight: number; negated: boolean }
export interface FeatureContribution { feature: string; contribution: number }
export interface ClassifierResult { label: Sentiment; probabilities: Record<string, number>; top_features: FeatureContribution[] }
export interface RuleResult { label: Sentiment; probabilities: Record<string, number>; positive_mass: number; negative_mass: number; cues: Cue[] }
export interface EngineInfo { id: "tfidf-logreg+rules" | "rules-fallback"; name: string; classifier_loaded: boolean; note: string }
export interface SentimentAnalysis {
  label: Sentiment; confidence: number; probabilities: Record<string, number>; mixed: boolean; uncertain: boolean;
  uncertainty_reasons: string[]; explanation: string; engine: EngineInfo; classifier: ClassifierResult | null;
  rules: RuleResult; truncated: boolean;
}
export interface IntentResult { intent: string; ambiguous: boolean; secondary: string[]; evidence: string[] }
export interface Topic { phrase: string; ref: string; kind: string; from_context: boolean }
export interface ContextInfo { is_followup: boolean; previous_sentiment: Sentiment | null; sentiment_shift: boolean; continued_topics: string[]; turns_in_memory: number }
export interface Analysis { sentiment: SentimentAnalysis; intent: IntentResult; topics: Topic[]; topic_method: string; context: ContextInfo | null }
export interface Fallback { used: boolean; reason: string | null; detail: string | null }
export interface ChatResponse {
  session_id: string; reply: string; reply_source: "local" | "llm"; provider: string | null; mode_requested: Mode;
  fallback: Fallback; safety_response: boolean; analysis: Analysis;
}
export interface ProviderStatus { id: string; label: string; configured: boolean; model: string; connection: "untested" | "ok" | "failed"; last_error: string | null }
export interface Capabilities {
  version: string; engine: EngineInfo; modes: Mode[]; default_mode: Mode; providers: ProviderStatus[];
  default_provider: string | null; max_message_chars: number; local_requires_network: boolean;
}
export interface AnalyticsActivity { hour: string; requests: number; failures: number }
export interface AnalyticsSnapshot {
  total_requests: number; success_count: number; failure_count: number; fallback_count: number;
  provider_failure_count: number; average_latency_ms: number | null;
  sentiment_counts: Record<Sentiment, number>; source_counts: Record<string, number>;
  provider_usage: Record<string, number>; mode_usage: Record<string, number>;
  activity: AnalyticsActivity[]; retention_limit: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  response?: ChatResponse; // assistant messages carry the full analysis
  analysisFor?: Analysis; // user messages link to the analysis of their text
}
