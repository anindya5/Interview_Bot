# This file will hold the InterviewSession class.
import uuid
import json
from scorecard import generate_llm_answer, calculate_similarity
from utilities.llm import call_gemini_api
from utilities.constants import DIFFICULTY_LEVELS

class InterviewSession:
    def __init__(self, topic, name, email, session_id=None):
        self.session_id = session_id if session_id else str(uuid.uuid4())
        self.topic = topic
        self.name = name
        self.email = email
        self.questions_and_answers = []
        self.question_count = 0  # total questions asked
        self.current_question = None
        # Difficulty management
        self.difficulty_levels = list(DIFFICULTY_LEVELS)
        self.level_index = 0  # 0..4
        self.phase = 'main'   # 'main' or 'followup' for each level
        # Track unique initial questions to avoid repetition
        self.initial_questions = []

    def to_dict(self):
        return {
            'session_id': self.session_id,
            'topic': self.topic,
            'name': self.name,
            'email': self.email,
            'questions_and_answers': json.dumps(self.questions_and_answers),
            'question_count': self.question_count,
            'current_question': self.current_question or '',  # Convert None to empty string
            'level_index': self.level_index,
            'phase': self.phase,
            'difficulty_levels': json.dumps(self.difficulty_levels),
            'initial_questions': json.dumps(self.initial_questions),
        }

    @classmethod
    def from_dict(cls, data):
        session = cls(data['topic'], data['name'], data['email'], session_id=data['session_id'])
        session.questions_and_answers = json.loads(data.get('questions_and_answers', '[]'))
        session.question_count = int(data.get('question_count', 0))
        session.current_question = data.get('current_question')
        # Backward-compatible loads
        try:
            session.level_index = int(data.get('level_index', 0))
        except (TypeError, ValueError):
            session.level_index = 0
        session.phase = data.get('phase', 'main') or 'main'
        try:
            session.difficulty_levels = json.loads(data.get('difficulty_levels', '[]')) or [
                'very easy', 'easy', 'medium', 'hard', 'very hard'
            ]
        except json.JSONDecodeError:
            session.difficulty_levels = ['very easy', 'easy', 'medium', 'hard', 'very hard']
        try:
            session.initial_questions = json.loads(data.get('initial_questions', '[]'))
        except json.JSONDecodeError:
            session.initial_questions = []
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
        # Start at level 0 (very easy), main question
        self.level_index = 0
        self.phase = 'main'
        self.question_count = 1
        difficulty = self.difficulty_levels[self.level_index]
        prompt = (
            f"Your task is to generate a single, open-ended interview question about the topic: {self.topic}. Ask {difficulty} technical question on the topic ."
            f"Return only the question itself, with no extra text or explanation"
        )
        question = self._call_gemini_api(prompt)
        self.current_question = question
        # Record unique initial
        self.initial_questions.append(question)
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
        
        # Build conversation history for context
        conversation_history = ""
        for qa in self.questions_and_answers:
            conversation_history += f"Q: {qa['question']}\nA: {qa['answer']}\n\n"

        # Determine next prompt based on phase
        difficulty = self.difficulty_levels[self.level_index]
        if self.phase == 'main':
            # Next should be a follow-up at the same difficulty
            prompt = (
                "You are an expert interviewer. Based on the conversation history and the candidate's last answer, "
                "ask a probing follow-up question that digs deeper into specifics just discussed. "
                f"Internally target difficulty: {difficulty}. Do NOT mention or allude to difficulty. "
                "Be concise and focused on the last answer. Return ONLY the question text.\n\n"
                f"Conversation History:\n{conversation_history}\n"
                f"Candidate's Last Answer: \"{last_answer}\""
            )
            # Switch to follow-up phase (we are generating the follow-up now)
            self.phase = 'followup'
            question = self._call_gemini_api(prompt)
        else:
            # We just asked follow-up previously; advance difficulty level and ask a new main question
            if self.level_index < len(self.difficulty_levels) - 1:
                self.level_index += 1
            difficulty = self.difficulty_levels[self.level_index]
            base_prompt = (
                f"You are an expert interviewer. Craft a single, open-ended QUESTION on the topic '{self.topic}'. "
                f"It must be technical and distinct from any previous initial questions. "
                f"Internally target difficulty: {difficulty}. Do NOT mention or allude to difficulty levels. "
                f"Keep language natural and conversational. Return ONLY the question text."
            )
            # Try to ensure uniqueness from prior initials
            question = self._call_gemini_api(base_prompt)
            retries = 2
            while retries >= 0 and question in self.initial_questions:
                avoid_list = " | ".join(self.initial_questions[-5:])  # include last few initials
                prompt = (
                    base_prompt +
                    f" Ensure it is not similar to any of these: {avoid_list}."
                )
                question = self._call_gemini_api(prompt)
                retries -= 1
            # Record unique initial (even if retries exhausted, record to move on)
            self.initial_questions.append(question)
            self.phase = 'main'

        self.current_question = question
        self.questions_and_answers.append({"question": question, "answer": "", "score": 0.0, "llm_answer": ""})
        return question

    def _call_gemini_api(self, prompt, retries=3, backoff_factor=2):
        # Delegate to utilities.llm for a single integration point
        return call_gemini_api(prompt, retries=retries, backoff_factor=backoff_factor)