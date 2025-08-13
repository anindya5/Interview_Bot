# This file will hold the InterviewSession class.
import requests
import uuid
import time
import json
from config import API_URL
from scorecard import generate_llm_answer, calculate_similarity

class InterviewSession:
    def __init__(self, topic, name, email, session_id=None):
        self.session_id = session_id if session_id else str(uuid.uuid4())
        self.topic = topic
        self.name = name
        self.email = email
        self.questions_and_answers = []
        self.question_count = 0 # 0: initial, 1: followup, 2: leading
        self.current_question = None

    def to_dict(self):
        return {
            'session_id': self.session_id,
            'topic': self.topic,
            'name': self.name,
            'email': self.email,
            'questions_and_answers': json.dumps(self.questions_and_answers),
            'question_count': self.question_count,
            'current_question': self.current_question or '' # Convert None to empty string
        }

    @classmethod
    def from_dict(cls, data):
        session = cls(data['topic'], data['name'], data['email'], session_id=data['session_id'])
        session.questions_and_answers = json.loads(data.get('questions_and_answers', '[]'))
        session.question_count = int(data.get('question_count', 0))
        session.current_question = data.get('current_question')
        return session

    def save(self, r):
        if r:
            r.hset(f"session:{self.session_id}", mapping=self.to_dict())

    @classmethod
    def load(cls, r, session_id):
        if r:
            data = r.hgetall(f"session:{session_id}")
            if data:
                return cls.from_dict(data)
        return None

    def generate_initial_question(self):
        self.question_count = 1
        prompt = f"""Your task is to generate a single, open-ended interview question about the topic: {self.topic}. Ask technical question if the topic is technical otherwise just focus on the topic. Return only the question itself, with no extra text or explanation."""
        question = self._call_gemini_api(prompt)
        self.current_question = question
        # Initialize the Q&A entry with placeholders for the score and LLM answer
        self.questions_and_answers.append({"question": question, "answer": "", "score": 0.0, "llm_answer": ""})
        return question

    def generate_next_question(self, last_answer):
        # --- Scoring Logic Start ---
        if self.questions_and_answers:
            # Get the question the candidate just answered
            last_question = self.questions_and_answers[-1]['question']
            
            # Update the candidate's answer
            self.questions_and_answers[-1]['answer'] = last_answer
            
            # Generate the ideal LLM answer for scoring
            llm_answer = generate_llm_answer(last_question, self.topic)
            self.questions_and_answers[-1]['llm_answer'] = llm_answer
            
            # Calculate and store the similarity score
            score = calculate_similarity(last_answer, llm_answer)
            self.questions_and_answers[-1]['score'] = score
            print(f"[SCORE] For Q: '{last_question[:50]}...', Score: {score:.2f}")
        # --- Scoring Logic End ---

        self.question_count += 1
        
        conversation_history = ""
        for qa in self.questions_and_answers:
            conversation_history += f"Q: {qa['question']}\nA: {qa['answer']}\n\n"

        if self.question_count == 2:
            # Follow-up question
            prompt = f"""You are an interviewer. Based on the following conversation history, ask a relevant follow-up question that digs deeper into the candidate's last answer. 

Conversation History:
{conversation_history}

Candidate's Last Answer (for emphasis): \"{last_answer}\"

Your task: Generate a single follow-up question. Return only the question itself."""
        elif self.question_count == 3:
            # Leading question
            prompt = f"""You are an interviewer. Based on the conversation history, ask a final, broader question that leads the candidate to discuss related concepts or a higher-level perspective on the topic. 

Conversation History:
{conversation_history}

Your task: Generate a single leading question. Return only the question itself."""
        else:
            # Should not happen in the current 3-question flow
            return "Error: Unexpected question count."

        question = self._call_gemini_api(prompt)
        self.current_question = question
        self.questions_and_answers.append({"question": question, "answer": "", "score": 0.0, "llm_answer": ""})
        return question

    def _call_gemini_api(self, prompt, retries=3, backoff_factor=2):
        headers = {'Content-Type': 'application/json'}
        data = {'contents': [{'parts': [{'text': prompt}]}]}
        
        for i in range(retries):
            try:
                response = requests.post(API_URL, headers=headers, json=data, timeout=120)
                response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
                
                response_json = response.json()
                
                # Navigate the JSON structure carefully
                if 'candidates' in response_json and len(response_json['candidates']) > 0:
                    candidate = response_json['candidates'][0]
                    if 'content' in candidate and 'parts' in candidate['content'] and len(candidate['content']['parts']) > 0:
                        return candidate['content']['parts'][0]['text'].strip()
                
                # Handle cases where the expected structure is not present
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