import time
import requests
from config import API_URL
from typing import Optional


def _build_request(prompt: str):
    """Build request headers and JSON payload for the LLM endpoint.

    The payload matches the structure expected by Google/Gemini-style APIs:
    {
      "contents": [ { "parts": [ { "text": <prompt> } ] } ]
    }

    Keeping this centralized ensures the structure stays in sync with
    `_extract_text()` which parses the corresponding response shape.

    Args:
        prompt: The prompt/question to send to the model.

    Returns:
        A tuple of (headers, data) ready to pass to requests.post.
    """
    headers = {'Content-Type': 'application/json'}
    data = {'contents': [{'parts': [{'text': prompt}]}]}
    return headers, data


def _extract_text(response_json: dict) -> Optional[str]:
    """Extract plain text from a Gemini-style response JSON.

    Expected shape (minimal):
    {
      "candidates": [
        { "content": { "parts": [ { "text": "..." } ] } }
      ]
    }

    The function is intentionally defensive:
    - Returns None if any of the expected keys/arrays are missing/empty.
    - Strips the text if found; otherwise returns None.

    Args:
        response_json: Parsed JSON from the API response.

    Returns:
        The extracted text, or None when format does not match expectations.
    """
    candidates = response_json.get('candidates') or []
    if not candidates:
        return None
    candidate = candidates[0]
    content = candidate.get('content') or {}
    parts = content.get('parts') or []
    if not parts:
        return None
    text = parts[0].get('text')
    return text.strip() if isinstance(text, str) else None


def _backoff_sleep(attempt: int, backoff_factor: int) -> None:
    """Sleep using exponential backoff based on the attempt number.

    The wait time is computed as `backoff_factor ** attempt` and printed
    for observability during local development/tests.

    Args:
        attempt: Zero-based attempt index within the retry loop.
        backoff_factor: Base used for exponentiation (e.g., 2 -> 1,2,4,... seconds).
    """
    wait_time = max(0, backoff_factor ** attempt)
    if wait_time:
        print(f"Rate limit exceeded. Retrying in {wait_time} seconds...")
        time.sleep(wait_time)


def call_gemini_api(prompt: str, retries: int = 3, backoff_factor: int = 2) -> str:
    """Call the LLM API with simple retry and response parsing.

    Behavior:
    - Builds request via `_build_request()`.
    - Attempts up to `retries` times.
      * On HTTP 429, sleeps with `_backoff_sleep()` then retries.
      * On other HTTP errors, returns an error string including status code.
      * On network errors (RequestException), retries until attempts exhausted.
    - On 2xx, parses JSON and extracts text via `_extract_text()`.
      * If text is missing or payload shape is unexpected, returns a descriptive error.

    Args:
        prompt: Prompt/question to send to the model.
        retries: Max attempts (default 3). Each iteration performs one POST.
        backoff_factor: Base for exponential backoff (default 2).

    Returns:
        On success: Extracted text string.
        On failure: Error string prefixed with "Error:" describing the issue.
    """
    headers, data = _build_request(prompt)

    for attempt in range(retries):
        try:
            resp = requests.post(API_URL, headers=headers, json=data, timeout=120)
            resp.raise_for_status()

            payload = resp.json()
            text = _extract_text(payload)
            if text:
                return text
            return f"Error: Unexpected API response format: {resp.text}"

        except requests.exceptions.HTTPError as e:
            status = getattr(e.response, 'status_code', None)
            if status == 429 and attempt < retries - 1:
                _backoff_sleep(attempt, backoff_factor)
                continue
            # Non-retryable HTTP error or no attempts left
            error_text = getattr(e.response, 'text', '')
            return f"Error: API request failed with status {status}: {error_text}"

        except requests.RequestException as e:
            # Network or other request error; only retry if attempts left
            if attempt < retries - 1:
                _backoff_sleep(attempt, backoff_factor)
                continue
            return f"Error: Request failed: {str(e)}"

    # Should not reach here due to returns in loop, but kept as a safeguard
    return "Error: Exhausted retries without a successful response"
