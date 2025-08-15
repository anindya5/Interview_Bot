import types
import requests
import pytest

import utilities.llm as llm


class _Resp:
    """
    Minimal response stub used to simulate requests.Response in tests.
    - raise_for_status() raises HTTPError for non-2xx statuses and attaches a
      lightweight .response object so the production code can read status/text.
    - json() returns the provided payload to mimic .json() behavior.
    """
    def __init__(self, status_code=200, json_payload=None, text=""):
        self.status_code = status_code
        self._json = json_payload if json_payload is not None else {}
        self.text = text or str(self._json)

    def raise_for_status(self):
        if not (200 <= self.status_code < 300):
            http_err = requests.exceptions.HTTPError()
            # Attach a minimal response-like object
            http_err.response = types.SimpleNamespace(status_code=self.status_code, text=self.text)
            raise http_err

    def json(self):
        return self._json


def test_call_gemini_api_success(monkeypatch):
    """
    When the API returns a well-formed payload with candidates/content/parts/text,
    call_gemini_api should extract and return the text content.
    """
    payload = {
        'candidates': [
            {'content': {'parts': [{'text': 'Hello world'}]}}
        ]
    }

    def _post(url, headers=None, json=None, timeout=0):
        return _Resp(200, payload)

    # Stub network and sleep to keep the test fast and deterministic
    monkeypatch.setattr(llm.requests, 'post', _post)
    # Avoid sleeping if any backoff path is accidentally hit
    monkeypatch.setattr(llm.time, 'sleep', lambda s: None)

    out = llm.call_gemini_api('prompt')
    assert out == 'Hello world'


def test_call_gemini_api_429_then_success(monkeypatch):
    """
    If the first call returns HTTP 429 (rate limit), the function should back off
    and retry. On the next successful response it should return the text.
    """
    calls = {'n': 0}

    def _post(url, headers=None, json=None, timeout=0):
        if calls['n'] == 0:
            calls['n'] += 1
            return _Resp(429, text='rate limited')
        return _Resp(200, {
            'candidates': [
                {'content': {'parts': [{'text': 'Recovered'}]}}
            ]
        })

    monkeypatch.setattr(llm.requests, 'post', _post)
    monkeypatch.setattr(llm.time, 'sleep', lambda s: None)

    out = llm.call_gemini_api('prompt', retries=3, backoff_factor=1)
    assert out == 'Recovered'
    assert calls['n'] == 1  # first call was 429 (incremented once)


def test_call_gemini_api_malformed_payload(monkeypatch):
    """
    If the payload is missing expected keys (e.g., 'candidates'), the function
    should return a descriptive error string rather than crashing.
    """
    # No candidates key
    def _post(url, headers=None, json=None, timeout=0):
        return _Resp(200, {'foo': 'bar'}, text='{}')

    monkeypatch.setattr(llm.requests, 'post', _post)
    out = llm.call_gemini_api('prompt')
    assert out.startswith('Error: Unexpected API response format:')


def test_call_gemini_api_http_error_non_retry(monkeypatch):
    """
    For non-retryable HTTP errors (e.g., 400), the function should return an
    error string including the status code.
    """
    def _post(url, headers=None, json=None, timeout=0):
        return _Resp(400, text='bad request')

    monkeypatch.setattr(llm.requests, 'post', _post)
    out = llm.call_gemini_api('prompt')
    assert 'status 400' in out


def test_call_gemini_api_network_error_retries_then_fail(monkeypatch):
    """
    For network-level exceptions (RequestException), the function should retry
    up to the configured limit and then return an error string.
    """
    calls = {'n': 0}

    def _post(url, headers=None, json=None, timeout=0):
        calls['n'] += 1
        raise requests.RequestException('net down')

    monkeypatch.setattr(llm.requests, 'post', _post)
    monkeypatch.setattr(llm.time, 'sleep', lambda s: None)

    out = llm.call_gemini_api('prompt', retries=2, backoff_factor=1)
    assert out.startswith('Error: Request failed:')
    assert calls['n'] == 2  # 2 attempts total with retries=2
