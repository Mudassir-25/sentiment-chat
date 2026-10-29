"""Ties analysis, context, mode selection, local/LLM reply generation and fallback together.

Mode rules:
  local_only  -> never calls an LLM.
  automatic   -> LLM if a provider is configured, else local (no fallback flag: nothing failed).
  ai_enhanced -> LLM if configured; if missing or failing, local with an explicit fallback record.
Sentiment/intent/topics always come from the local engine; the LLM only writes the reply.
"""
from __future__ import annotations

import logging
import random

from app.conversation.context import SessionStore, Turn, apply_context
from app.conversation.responses import build_reply
from app.conversation.safety import SAFETY_REPLY, is_crisis
from app.llm.base import ProviderError
from app.llm.factory import LLMRegistry
from app.llm.prompt import SYSTEM, build_messages, sanitize
from app.nlp.intent import detect_intent
from app.nlp.preprocessing import preprocess
from app.nlp.sentiment import SentimentEngine
from app.nlp.topics import extract_topics
from app.schemas import Analysis, ChatRequest, ChatResponse, Fallback

log = logging.getLogger("sentiment_chat.orchestrator")


class Orchestrator:
    def __init__(self, engine: SentimentEngine, store: SessionStore, registry: LLMRegistry,
                 rng: random.Random | None = None) -> None:
        self.engine, self.store, self.registry = engine, store, registry
        self.rng = rng or random.Random()

    def analyze(self, text: str) -> Analysis:
        p = preprocess(text)
        s = self.engine.analyze(text)
        return Analysis(sentiment=s, intent=detect_intent(p, s), topics=extract_topics(p))

    async def chat(self, req: ChatRequest) -> ChatResponse:
        session = self.store.get(req.session_id)
        analysis = apply_context(session, req.message, self.analyze(req.message))
        fallback = Fallback(used=False)
        source, provider_id, safety = "local", None, False
        reply, tpl_id = "", None

        if is_crisis(req.message):
            reply, safety = SAFETY_REPLY, True
        else:
            provider = None if req.mode == "local_only" else self.registry.resolve(req.provider)
            if provider is not None:
                try:
                    history = [(t.user_text, t.reply) for t in session.turns]
                    raw = await provider.generate(SYSTEM, build_messages(req.message, analysis, history))
                    clean = sanitize(raw)
                    if not clean:
                        raise ProviderError("empty_response", "The provider returned an empty reply.")
                    reply, source, provider_id = clean, "llm", provider.id
                    self.registry.record_ok(provider.id)
                except ProviderError as e:
                    log.warning("llm failed category=%s provider=%s; using local reply", e.category, provider.id)
                    self.registry.record_error(provider.id, e)
                    fallback = Fallback(used=True, reason=e.category, detail=e.public_message)
            elif req.mode != "local_only" and req.provider:
                fallback = Fallback(used=True, reason="provider_not_configured",
                                    detail="The selected AI provider is not configured. Check its backend environment variables.")
            elif req.mode == "ai_enhanced":
                fallback = Fallback(used=True, reason="no_provider_configured",
                                    detail="AI enhanced mode was selected but no provider is configured.")
            if source == "local":
                reply, tpl_id = build_reply(analysis, list(session.recent_templates), self.rng)

        if tpl_id:
            session.recent_templates.append(tpl_id)
        session.turns.append(Turn(req.message, reply, analysis.sentiment.label, analysis.intent.intent, analysis.topics))
        log.info("chat handled mode=%s source=%s fallback=%s chars=%d", req.mode, source, fallback.reason, len(req.message))
        return ChatResponse(session_id=req.session_id, reply=reply, reply_source=source,  # type: ignore[arg-type]
                            provider=provider_id, mode_requested=req.mode, fallback=fallback,
                            safety_response=safety, analysis=analysis)
