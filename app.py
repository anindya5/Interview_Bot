from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import os
from dotenv import load_dotenv
import requests
import uuid
import time

load_dotenv()

app = Flask(__name__)
CORS(app)

# Gemini API configuration
API_KEY = os.getenv('GEMINI_API_KEY')
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro-latest:generateContent?key={API_KEY}"

sessions = {}

class InterviewSession:
    def __init__(self, topic):
        self.session_id = str(uuid.uuid4())
        self.topic = topic
        self.questions_and_answers = []
        self.question_count = 0 # 0: initial, 1: followup, 2: leading
        self.current_question = None

    def generate_initial_question(self):
        self.question_count = 1
        prompt = f"""Your task is to generate a single, open-ended technical interview question about the topic: {self.topic}. Return only the question itself, with no extra text or explanation."""
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        headers = {'Content-Type': 'application/json'}
        
        retries = 3
        for i in range(retries):
            try:
                response = requests.post(API_URL, json=payload, headers=headers)
                response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
                data = response.json()

                # Safely extract the text
                self.current_question = data['candidates'][0]['content']['parts'][0]['text'].strip()
                self.questions_and_answers.append({"question": self.current_question, "answer": ""})
                return self.current_question # Success

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429 and i < retries - 1:
                    wait = (2 ** i) + 2
                    print(f"[GEMINI API RATE LIMIT] Retrying in {wait}s...")
                    time.sleep(wait)
                    continue
                print(f"[GEMINI API REQUEST ERROR] {e}")
                self.current_question = "Error: Could not connect to the AI model."
                break
            except (KeyError, IndexError, TypeError) as e:
                print(f"[GEMINI API RESPONSE PARSE ERROR] {e}")
                if 'response' in locals():
                    print(f"[GEMINI API RAW RESPONSE] {response.text}")
                self.current_question = "Error: Could not parse the AI's response."
                break
        
        return self.current_question

    def generate_followup(self, candidate_response):
        # Update the last Q&A pair with the candidate's response
        if self.questions_and_answers:
            self.questions_and_answers[-1]["answer"] = candidate_response

        previous_qa = ""
        if len(self.questions_and_answers) > 0:
            # Consolidate all previous Q&As for context
            history = "\n".join([f"Q: {qa['question']}\nA: {qa['answer']}" for qa in self.questions_and_answers])
            previous_qa = f"Here is the interview history so far:\n{history}"

        if self.question_count == 1:
            # First follow-up: dig deeper
            prompt_instruction = "Based on the candidate's last answer, ask a single follow-up question to dig deeper into their reasoning or experience."
        else:
            # Second follow-up: ask a leading question to a new aspect
            prompt_instruction = "Based on the interview history, ask a single, more advanced or related leading question that explores a new aspect of the main topic."

        prompt = f"""You are an expert technical interviewer.
        Main Topic: {self.topic}
        {previous_qa}

        Your task: {prompt_instruction}

        Return only the new question itself, with no extra text or explanation."""

        self.question_count += 1

        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        headers = {'Content-Type': 'application/json'}

        retries = 3
        for i in range(retries):
            try:
                response = requests.post(API_URL, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

                self.current_question = data['candidates'][0]['content']['parts'][0]['text'].strip()
                self.questions_and_answers.append({"question": self.current_question, "answer": ""})
                return self.current_question # Success

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429 and i < retries - 1:
                    wait = (2 ** i) + 2
                    print(f"[GEMINI API RATE LIMIT] Retrying in {wait}s...")
                    time.sleep(wait)
                    continue
                print(f"[GEMINI API FOLLOWUP REQUEST ERROR] {e}")
                self.current_question = "Error: Could not connect to the AI model for a follow-up."
                break
            except (KeyError, IndexError, TypeError) as e:
                print(f"[GEMINI API FOLLOWUP RESPONSE PARSE ERROR] {e}")
                if 'response' in locals():
                    print(f"[GEMINI API RAW RESPONSE] {response.text}")
                self.current_question = "Error: Could not parse the AI's follow-up response."
                break
        
        return self.current_question

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')

@app.route('/start-interview', methods=['POST'])
def start_interview():
    data = request.get_json()
    topic = data.get('topic')
    if not topic:
        return jsonify({'error': 'Topic is required.'}), 400

    session = InterviewSession(topic)
    sessions[session.session_id] = session
    initial_question = session.generate_initial_question()
    
    if initial_question.startswith("Error:"):
        return jsonify({'error': initial_question}), 500

    return jsonify({
        'session_id': session.session_id,
        'question': initial_question
    })

@app.route('/submit', methods=['POST'])
def submit():
    data = request.get_json()
    session_id = data.get('session_id')
    answer = data.get('answer')

    if not session_id or session_id not in sessions:
        return jsonify({'error': 'Invalid session ID', 'finished': True}), 400

    current_session = sessions[session_id]

    if current_session.question_count >= 5:
        # The last answer was for the final question. End of interview.
        if current_session.questions_and_answers:
             current_session.questions_and_answers[-1]["answer"] = answer
        transcript = "\n".join([f"Q: {qa['question']}\nA: {qa['answer']}" for qa in current_session.questions_and_answers])
        print(f"--- FINAL TRANSCRIPT ---\n{transcript}")
        return jsonify({'question': 'Thank you for your time! The interview is now complete.', 'finished': True})

    # Generate follow-up or leading question
    next_question = current_session.generate_followup(answer)

    if next_question.startswith("Error:"):
        return jsonify({'error': next_question, 'finished': True}), 500

    return jsonify({'question': next_question, 'finished': False})

if __name__ == '__main__':
    app.run(debug=True, port=5001)
