def test_app_factory_creates_app(app):
    # App fixture comes from tests/conftest.py
    assert app is not None
    assert app.testing is True


def test_routes_registered(client):
    # Basic smoke checks that endpoints exist (not asserting full behavior here)
    assert client.post('/start-interview', json={}).status_code in (200, 400)
    assert client.post('/submit', json={}).status_code in (200, 400)
    assert client.post('/onboarding/start').status_code == 200
