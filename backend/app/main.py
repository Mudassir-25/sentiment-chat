from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.conversation.context import SessionStore
from app.conversation.orchestrator import Orchestrator
from app.core.analytics import AnalyticsMiddleware, AnalyticsStore
from app.core.config import Settings
from app.core.logging import configure_logging
from app.llm.factory import LLMRegistry
from app.nlp.sentiment import SentimentEngine


def create_app(settings: Settings | None = None, engine: SentimentEngine | None = None) -> FastAPI:
    settings = settings or Settings()
    configure_logging(settings.log_level, settings.secret_values())
    app = FastAPI(title="Sentiment Chat API", version=settings.app_version)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list,
                       allow_methods=["GET", "POST", "DELETE"], allow_headers=["Content-Type"])
    app.state.analytics = AnalyticsStore()
    app.add_middleware(AnalyticsMiddleware, metrics=app.state.analytics)
    engine = engine if engine is not None else SentimentEngine.load(settings.resolved_model_path)
    app.state.settings = settings
    app.state.orchestrator = Orchestrator(engine, SessionStore(), LLMRegistry(settings))
    app.include_router(router)
    return app


app = create_app()
