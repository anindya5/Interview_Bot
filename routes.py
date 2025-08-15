from flask import Blueprint, request, jsonify, render_template, send_from_directory
from interview_logic import InterviewSession
from scorecard import generate_llm_answer, calculate_similarity
from models import Interview, Result
from onboarding import OnboardingSession

# Create a Flask Blueprint to organize routes
main_bp = Blueprint('main', __name__)

# Store connection objects from the app factory
r = None
db = None

def init_app(app, redis_conn, db_conn):
    global r, db
    r = redis_conn
    db = db_conn
    """Initializes the routes and registers the blueprint with the Flask app."""

    # === Core Application Routes ===

    @main_bp.route('/')
    def index():
        """Serves the main index.html page, which is the entry point of the web app."""
        return render_template('index.html')

    @main_bp.route('/static/<path:path>')
    def send_static(path):
        """Serves static files (e.g., CSS, JavaScript)."""
        return send_from_directory('static', path)

    @main_bp.route('/favicon.ico')
    def favicon():
        """Serves the favicon icon."""
        return send_from_directory(app.root_path, 'static/favicon.ico', mimetype='image/vnd.microsoft.icon')

    # === API Endpoints for Interview Flow ===

    @main_bp.route('/start-interview', methods=['POST'])
    def start_interview():
        """Starts a new interview session.
        
        Expects a JSON payload with 'topic', 'name', and 'email' keys.
        Creates a new InterviewSession, generates the first question, saves it to Redis,
        and returns the session_id and initial question to the client.
        """
        data = request.get_json()
        topic = data.get('topic')
        name = data.get('name')
        email = data.get('email')

        if not all([topic, name, email]):
            return jsonify({'error': 'Topic, name, and email are required.'}), 400

        # Create a new session with all candidate details
        session = InterviewSession(topic, name, email)
        session.save(r)
        
        # Generate the first question and update the session state in Redis
        initial_question = session.generate_initial_question()
        session.save(r) 
        
        if initial_question.startswith("Error:"):
            return jsonify({'error': initial_question}), 500
        
        # Return the new session ID so the client can continue the conversation
        return jsonify({'session_id': session.session_id, 'question': initial_question})

    @main_bp.route('/submit', methods=['POST'])
    def submit():
        """
        Handles answer submission from the client.
        - Expects 'session_id' and 'answer' in the JSON payload.
        - Loads the session from Redis.
        - If the interview is not over, generates the next question.
        - If the interview is over (3 questions answered), it calculates the final score,
          logs the transcript, cleans up the session, and notifies the client.
        """
        data = request.get_json()
        session_id = data.get('session_id')
        answer = data.get('answer')

        # Fail fast if Redis is not available
        if not r:
            return jsonify({'error': 'Database connection not available.', 'finished': True}), 500

        if not session_id or not answer:
            return jsonify({'error': 'Session ID and answer are required.'}), 400

        current_session = InterviewSession.load(r, session_id)
        if not current_session:
            return jsonify({'error': 'Session expired or not found.', 'finished': True}), 404

        # Check if the interview is over (after the 3rd question is answered)
        if current_session.question_count >= 3:
            # --- Final Scoring Logic ---
            last_question = current_session.questions_and_answers[-1]['question']
            llm_answer = generate_llm_answer(last_question, current_session.topic)
            score = calculate_similarity(answer, llm_answer)
            
            # Update the last record with the final answer, llm_answer, and score
            current_session.questions_and_answers[-1]['answer'] = answer
            current_session.questions_and_answers[-1]['llm_answer'] = llm_answer
            current_session.questions_and_answers[-1]['score'] = score
            # --- End Final Scoring ---

            # Calculate average score
            total_score = sum(qa['score'] for qa in current_session.questions_and_answers)
            average_score = total_score / len(current_session.questions_and_answers) if current_session.questions_and_answers else 0.0

            # Build a detailed transcript for server-side logging
            transcript = f"\n--- FINAL SCORECARD FOR {current_session.name.upper()} ---\n"
            transcript += f"Email: {current_session.email}\nTopic: {current_session.topic}\n"
            transcript += f"FINAL AVERAGE SCORE: {average_score:.2f}\n"
            transcript += "--------------------------------------------------\n"
            for i, qa in enumerate(current_session.questions_and_answers):
                transcript += f"Q{i+1}: {qa['question']}\n"
                transcript += f"A: {qa['answer']}\n"
                transcript += f"Score: {qa['score']:.2f}\n\n"
            transcript += "--------------------------------------------------\n"
            print(transcript)
            
            # --- Database Logging ---
            # Create a new Interview record and associated Result records
            try:
                new_interview = Interview(
                    candidate_name=current_session.name,
                    candidate_email=current_session.email,
                    topic=current_session.topic,
                    average_score=average_score
                )
                db.session.add(new_interview)
                db.session.flush()  # Use flush to get the ID for the new_interview

                for qa in current_session.questions_and_answers:
                    new_result = Result(
                        interview_id=new_interview.id,
                        question=qa['question'],
                        answer=qa.get('answer', ''),
                        score=qa.get('score', 0.0)
                    )
                    db.session.add(new_result)
                
                db.session.commit()
                print(f"Successfully saved interview for {current_session.name} to the database.")
            except Exception as e:
                db.session.rollback()
                print(f"Database error: {e}")
                # Optionally, return an error to the user
                # return jsonify({'error': 'Could not save interview results.', 'finished': True}), 500
            # --- End Database Logging ---

            # Clean up the session from Redis
            r.delete(f"session:{session_id}")
            
            # Signal to the client that the interview is finished, without displaying the score
            return jsonify({'question': 'Thank you for your time! The interview is now complete.', 'finished': True})

        # If the interview is not over, generate the next question
        next_question = current_session.generate_next_question(answer)
        current_session.save(r) # Save the updated state to Redis

        if next_question.startswith("Error:"):
            return jsonify({'error': next_question, 'finished': True}), 500
        
        # Return the next question to the client
        return jsonify({'question': next_question, 'finished': False})

    # Onboarding endpoints
    @main_bp.route('/onboarding/start', methods=['POST'])
    def onboarding_start():
        if not r:
            return jsonify({'error': 'Database connection not available.'}), 500
        session = OnboardingSession(r)
        payload = session.start()
        return jsonify({'onboarding_session_id': payload['session_id'], 'message': payload['message'], 'finished': payload['finished']})

    @main_bp.route('/onboarding/continue', methods=['POST'])
    def onboarding_continue():
        if not r:
            return jsonify({'error': 'Database connection not available.'}), 500
        data = request.get_json() or {}
        session_id = data.get('onboarding_session_id')
        user_message = data.get('message', '')
        if not session_id:
            return jsonify({'error': 'onboarding_session_id is required'}), 400
        session = OnboardingSession.load(r, session_id)
        if not session:
            return jsonify({'error': 'Onboarding session not found'}), 404
        result = session.continue_flow(user_message)
        resp = {'message': result.get('message', ''), 'finished': result.get('finished', False)}
        for key in ['candidate', 'stage', 'resend_available_in', 'expires_in', 'attempts_left']:
            if key in result:
                resp[key] = result[key]
        return jsonify(resp)

    @main_bp.route('/onboarding/resend', methods=['POST'])
    def onboarding_resend():
        if not r:
            return jsonify({'error': 'Database connection not available.'}), 500
        data = request.get_json() or {}
        session_id = data.get('onboarding_session_id')
        if not session_id:
            return jsonify({'error': 'onboarding_session_id is required'}), 400
        session = OnboardingSession.load(r, session_id)
        if not session:
            return jsonify({'error': 'Onboarding session not found'}), 404
        result = session.resend()
        if 'error' in result:
            return jsonify(result), 400
        resp = {'message': result.get('message', ''), 'finished': result.get('finished', False)}
        for key in ['stage', 'resend_available_in', 'expires_in', 'attempts_left']:
            if key in result:
                resp[key] = result[key]
        return jsonify(resp)

    # Register the blueprint with the main Flask app
    app.register_blueprint(main_bp)
