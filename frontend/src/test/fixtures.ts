import type { Capabilities, ChatResponse } from "../types";

export const caps = (over: Partial<Capabilities> = {}): Capabilities => ({
  version: "1.0.0", max_message_chars: 1000, local_requires_network: false, default_mode: "automatic", default_provider: null,
  modes: ["automatic", "local_only", "ai_enhanced"],
  engine: { id: "tfidf-logreg+rules", name: "TF-IDF + Logistic Regression + rules", classifier_loaded: true, note: "Trained local classifier" },
  providers: [{ id: "openai", label: "OpenAI-compatible", configured: false, model: "m", connection: "untested", last_error: null },
              { id: "anthropic", label: "Anthropic", configured: false, model: "m", connection: "untested", last_error: null }],
  ...over,
});

export const chatResponse = (over: Partial<ChatResponse> = {}): ChatResponse => ({
  session_id: "s", reply: "Congratulations on your exam!", reply_source: "local", provider: null, mode_requested: "automatic",
  fallback: { used: false, reason: null, detail: null }, safety_response: false,
  analysis: {
    sentiment: {
      label: "positive", confidence: 0.82, probabilities: { negative: .05, neutral: .13, positive: .82 }, mixed: false, uncertain: false,
      uncertainty_reasons: [], explanation: "Classifier says positive. Overall: positive.", truncated: false,
      engine: { id: "tfidf-logreg+rules", name: "TF-IDF + Logistic Regression + rules", classifier_loaded: true, note: "" },
      classifier: { label: "positive", probabilities: {}, top_features: [{ feature: "passed", contribution: 1.2 }] },
      rules: { label: "positive", probabilities: {}, positive_mass: 1.6, negative_mass: 0, cues: [{ text: "passed", polarity: "positive", weight: 1.6, negated: false }] },
    },
    intent: { intent: "good_news", ambiguous: false, secondary: [], evidence: [] },
    topics: [{ phrase: "exam", ref: "your exam", kind: "noun_phrase", from_context: false }],
    topic_method: "lexical", context: { is_followup: false, previous_sentiment: null, sentiment_shift: false, continued_topics: [], turns_in_memory: 0 },
  },
  ...over,
});
