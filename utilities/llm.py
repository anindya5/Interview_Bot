import time
import requests
from config import API_URL


def call_gemini_api(prompt: str, retries: int = 3, backoff_factor: int = 2) -> str:
    headers = {'Content-Type': 'application/json'}
    data = {'contents': [{'parts': [{'text': prompt}]}]}

    for i in range(retries):
        try:
            response = requests.post(API_URL, headers=headers, json=data, timeout=120)
            response.raise_for_status()

            response_json = response.json()
            if 'candidates' in response_json and len(response_json['candidates']) > 0:
                candidate = response_json['candidates'][0]
                if 'content' in candidate and 'parts' in candidate['content'] and len(candidate['content']['parts']) > 0:
                    return candidate['content']['parts'][0]['text'].strip()
            return f"Error: Unexpected API response format: {response.text}"
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429 and i < retries - 1:
                wait_time = backoff_factor ** i
                print(f"Rate limit exceeded. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                return f"Error: API request failed with status {e.response.status_code}: {e.response.text}"
        except requests.exceptions.RequestException as e:
            return f"Error: API request failed: {e}"
        except (KeyError, IndexError) as e:
            return f"Error: Could not parse API response: {e} - Response: {response.text}"

    return "Error: API request failed after multiple retries."
