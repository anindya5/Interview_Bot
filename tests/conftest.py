import os
import sys
import pytest
import fakeredis
import importlib.util
from pathlib import Path

# Ensure repo root is on sys.path so tests can import top-level modules (e.g., interview_logic.py)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Ensure env for create_app
os.environ.setdefault('DATABASE_URL', 'sqlite:///:memory:')
os.environ.setdefault('REDIS_URL', 'redis://localhost:6379/0')


def _load_module_from_path(name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(name, str(file_path))
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader, f"Unable to load module spec for {file_path}"
    spec.loader.exec_module(module)
    return module


essential_modules_loaded = False

def _ensure_onboarding_module():
    """Load project onboarding.py and register as 'onboarding' to avoid tests/onboarding shadowing."""
    onboarding_path = Path(__file__).resolve().parents[1] / "onboarding.py"
    module = _load_module_from_path("project_onboarding", onboarding_path)
    sys.modules['onboarding'] = module


def _ensure_routes_module():
    """Load the real project routes.py and register it as 'routes' to avoid tests/routes shadowing."""
    routes_path = Path(__file__).resolve().parents[1] / "routes.py"
    module = _load_module_from_path("project_routes", routes_path)
    sys.modules['routes'] = module


def _load_create_app_from_file():
    """Load create_app from the project root app.py avoiding tests/app shadowing."""
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    module = _load_module_from_path("app_root_module", app_path)
    return module.create_app


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
    global essential_modules_loaded
    if not essential_modules_loaded:
        # Ensure proper onboarding and routes modules are present before app import
        _ensure_onboarding_module()
        _ensure_routes_module()
        essential_modules_loaded = True
    create_app = _load_create_app_from_file()
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
    # Keep InterviewSession behavior deterministic and include level/phase markers
    from interview_logic import InterviewSession
    def _fake_call(self, prompt: str, *a, **k):
        return f"Q[{self.level_index}-{self.phase}] {self.topic}"
    monkeypatch.setattr(InterviewSession, '_call_gemini_api', _fake_call)
    yield
