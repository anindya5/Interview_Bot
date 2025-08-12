from flask import Blueprint, request, jsonify, render_template, send_from_directory
from interview_logic import InterviewSession

# Create a Flask Blueprint to organize routes
main_bp = Blueprint('main', __name__)

def init_app(app, r):
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
        
        Expects a JSON payload with a 'topic' key.
        Creates a new InterviewSession, generates the first question, saves it to Redis,
        and returns the session_id and initial question to the client.
        """
        data = request.get_json()
        topic = data.get('topic')

        if not topic:
            return jsonify({'error': 'Topic is required.'}), 400

        # Create a new session and save it to Redis immediately
        session = InterviewSession(topic)
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
        """Handles a user's answer submission and returns the next question.
        
        Expects a JSON payload with 'session_id' and 'answer'.
        Loads the session from Redis, generates the next question, and determines if the interview is complete.
        """
        data = request.get_json()
        session_id = data.get('session_id')
        answer = data.get('answer')

        # Fail fast if Redis is not available
        if not r:
            return jsonify({'error': 'Database connection not available.', 'finished': True}), 500

        if not session_id:
            return jsonify({'error': 'Invalid session ID', 'finished': True}), 400

        # Load the existing session from Redis
        current_session = InterviewSession.load(r, session_id)
        if not current_session:
            return jsonify({'error': 'Session expired or not found.', 'finished': True}), 404

        # Check if the interview is over (after the 3rd question is answered)
        if current_session.question_count >= 3:
            # Record the final answer
            if current_session.questions_and_answers:
                 current_session.questions_and_answers[-1]["answer"] = answer
            
            # Print the final transcript to the server console for logging
            transcript = "\n".join([f"Q: {qa['question']}\nA: {qa['answer']}" for qa in current_session.questions_and_answers])
            print(f"--- FINAL TRANSCRIPT ---\n{transcript}")
            
            # Clean up the session from Redis
            r.delete(f"session:{session_id}")
            
            # Signal to the client that the interview is finished
            return jsonify({'question': 'Thank you for your time! The interview is now complete.', 'finished': True})

        # If the interview is not over, generate the next question
        next_question = current_session.generate_next_question(answer)
        current_session.save(r) # Save the updated state to Redis

        if next_question.startswith("Error:"):
            return jsonify({'error': next_question, 'finished': True}), 500
        
        # Return the next question to the client
        return jsonify({'question': next_question, 'finished': False})

    # Register the blueprint with the main Flask app
    app.register_blueprint(main_bp)
