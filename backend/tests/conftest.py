import random

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.llm.base import LLMProvider, ProviderError
from app.main import create_app
from app.nlp import training
from app.nlp.sentiment import SentimentEngine

SECRET = "sk-test-SECRET-1234567890abcdef"


class FakeProvider(LLMProvider):
    id, label, model = "openai", "Fake", "fake-model"

    def __init__(self, reply="AI reply about your day.", error: ProviderError | None = None):
        self.reply, self.error, self.calls = reply, error, 0
        self.last_messages = None

    async def generate(self, system, messages, max_tokens=300):
        self.calls += 1
        self.last_messages = messages
        if self.error:
            raise self.error
        return self.reply


@pytest.fixture(scope="session")
def model_path(tmp_path_factory):
    p = tmp_path_factory.mktemp("model") / "sentiment.joblib"
    training.train(p)
    return p


@pytest.fixture(scope="session")
def trained_engine(model_path):
    e = SentimentEngine.load(model_path)
    assert e.pipeline is not None
    return e


@pytest.fixture()
def fallback_engine():
    return SentimentEngine()


def make_client(engine, **kw):
    settings = Settings(_env_file=None, **kw)
    app = create_app(settings, engine)
    app.state.orchestrator.rng = random.Random(1)
    return TestClient(app), app


@pytest.fixture()
def client(trained_engine):
    c, app = make_client(trained_engine)
    c.app_ref = app
    return c


@pytest.fixture()
def ai_client(trained_engine):
    c, app = make_client(trained_engine, openai_api_key=SECRET)
    fake = FakeProvider()
    app.state.orchestrator.registry.providers["openai"] = fake
    c.fake, c.app_ref = fake, app
    return c


SID = "session-aaaa1111"


def chat(c, msg, sid=SID, **kw):
    r = c.post("/api/chat", json={"session_id": sid, "message": msg, **kw})
    assert r.status_code == 200, r.text
    return r.json()
