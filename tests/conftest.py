import os
import pytest
import fakeredis

# Ensure env for create_app
os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')

@pytest.fixture(scope='session')
def fake_redis_server():
    return fakeredis.FakeRedis(decode_responses=True)

@pytest.fixture(autouse=True)
def patch_redis(monkeypatch, fake_redis_server):
    import redis
    monkeypatch.setattr(redis, 'from_url', lambda *args, **kwargs: fake_redis_server)
    yield

@pytest.fixture()
def app():
    from app import create_app
    application = create_app()
    application.config.update(TESTING=True)
    return application

@pytest.fixture()
def client(app):
    return app.test_client()

@pytest.fixture()
def stub_email(monkeypatch):
    # Prevent real HTTP for sending emails via utilities layer
    import utilities.email as uemail
    monkeypatch.setattr(uemail, 'send_verification_email', lambda to, code: (True, None))
    yield

@pytest.fixture()
def stub_gemini(monkeypatch):
    # Make InterviewSession deterministic by patching utilities.llm
    import utilities.llm as ullm
    def _fake_call(prompt: str, *a, **k):
        # encodes level-phase requires access to InterviewSession; instead keep deterministic prefix
        return f"Q {prompt[:16]}"
    monkeypatch.setattr(ullm, 'call_gemini_api', _fake_call)
    yield
