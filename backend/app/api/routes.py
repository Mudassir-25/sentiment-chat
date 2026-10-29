from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from app.conversation.orchestrator import Orchestrator
from app.schemas import (SESSION_RE, Analysis, AnalyticsSnapshot, AnalyzeRequest, Capabilities, ChatRequest,
                         ChatResponse, ProviderStatus)

router = APIRouter(prefix="/api")


def _orch(request: Request) -> Orchestrator:
    return request.app.state.orchestrator


def _check_len(request: Request, text: str) -> None:
    limit = request.app.state.settings.max_message_chars
    if not text:
        raise HTTPException(422, "Message must not be empty.")
    if len(text) > limit:
        raise HTTPException(422, f"Message is too long (max {limit} characters).")


@router.get("/health")
def health(request: Request) -> dict:
    return {"status": "ok", "version": request.app.state.settings.app_version}


@router.get("/capabilities", response_model=Capabilities)
def capabilities(request: Request) -> Capabilities:
    o, st = _orch(request), request.app.state.settings
    return Capabilities(version=st.app_version, engine=o.engine.info,
                        modes=["automatic", "local_only", "ai_enhanced"], default_mode="automatic",
                        providers=o.registry.status(), default_provider=o.registry.default_provider,
                        max_message_chars=st.max_message_chars)


@router.get("/analytics", response_model=AnalyticsSnapshot)
def analytics(request: Request) -> AnalyticsSnapshot:
    return request.app.state.analytics.snapshot()


@router.post("/analyze", response_model=Analysis)
def analyze(body: AnalyzeRequest, request: Request) -> Analysis:
    _check_len(request, body.text)
    return _orch(request).analyze(body.text)


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request) -> ChatResponse:
    _check_len(request, body.message)
    return await _orch(request).chat(body)


@router.delete("/sessions/{session_id}")
def clear_session(session_id: str, request: Request) -> dict:
    if not SESSION_RE.match(session_id):
        raise HTTPException(422, "Invalid session id.")
    return {"cleared": _orch(request).store.clear(session_id)}


@router.post("/llm/{provider_id}/test", response_model=ProviderStatus)
async def test_provider(provider_id: str, request: Request) -> ProviderStatus:
    """Explicit user-triggered connection test (the only non-chat LLM request)."""
    try:
        return await _orch(request).registry.test(provider_id)
    except KeyError:
        raise HTTPException(404, "Provider is not configured.") from None
