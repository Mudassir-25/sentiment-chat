import type { Mode, Sentiment } from "../types";

export const SENTIMENT_LABEL: Record<Sentiment, string> = { positive: "Positive", neutral: "Neutral", negative: "Negative" };
export const MODE_LABEL: Record<Mode, string> = { automatic: "Automatic", local_only: "Local only", ai_enhanced: "AI enhanced" };
export const MODE_HELP: Record<Mode, string> = {
  automatic: "Use AI when a provider is configured; otherwise local NLP.",
  local_only: "Never contacts an AI provider. Sentiment and template replies run on the app backend.",
  ai_enhanced: "Use the configured provider, with a visible fallback to local NLP if it fails.",
};
export const INTENT_LABEL: Record<string, string> = {
  greeting: "Greeting", farewell: "Farewell", gratitude: "Gratitude", question: "Question", good_news: "Good news",
  frustration: "Frustration", sadness_stress: "Sadness / stress", excitement: "Excitement", encouragement: "Asks for encouragement",
  general: "General conversation", unknown: "Unclear",
};
export const FALLBACK_REASON: Record<string, string> = {
  no_provider_configured: "No AI provider is configured", invalid_key: "The provider rejected the API key",
  rate_limited: "Provider rate limit reached", timeout: "The provider timed out", network: "Could not reach the provider",
  provider_error: "The provider returned an error", empty_response: "The provider returned an empty reply",
  model_unavailable: "The configured provider model is unavailable", invalid_request: "The provider rejected its request",
  provider_not_configured: "The selected AI provider is not configured",
};
