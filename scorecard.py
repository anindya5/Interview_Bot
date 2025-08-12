import requests
import time
from config import API_URL
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

def generate_llm_answer(question, topic):
    """Asks the LLM to provide an ideal answer to a given interview question."""
    prompt = f"""You are a world-class expert in {topic}. Provide a concise, ideal answer to the following technical interview question. Focus on accuracy and clarity.

Question: {question}

Ideal Answer:"""
    # This internal function reuses the Gemini API call logic
    return _call_gemini_api(prompt)

def calculate_similarity(text1, text2):
    """Calculates the cosine similarity between two texts."""
    if not text1 or not text2:
        return 0.0

    try:
        vectorizer = TfidfVectorizer().fit_transform([text1, text2])
        vectors = vectorizer.toarray()
        similarity = cosine_similarity(vectors)
        # The result is a matrix, we need the value from the off-diagonal
        return similarity[0][1]
    except Exception as e:
        print(f"[Similarity Error] {e}")
        return 0.0

def _call_gemini_api(prompt, retries=3, backoff_factor=2):
    """A private helper to call the Gemini API, isolated for scoring purposes."""
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
                time.sleep(wait_time)
            else:
                return f"Error: API request failed with status {e.response.status_code}"
        except requests.exceptions.RequestException as e:
            return f"Error: API request failed: {e}"
    
    return "Error: API request failed after multiple retries."
