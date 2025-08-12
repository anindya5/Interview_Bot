# This file will hold the application routes.
from flask import Blueprint, request, jsonify, render_template, send_from_directory
from interview_logic import InterviewSession

main_bp = Blueprint('main', __name__)

def init_app(app, r):

    @main_bp.route('/')
    def index():
        return render_template('index.html')

    @main_bp.route('/static/<path:path>')
    def send_static(path):
        return send_from_directory('static', path)

    @main_bp.route('/favicon.ico')
    def favicon():
        return send_from_directory(app.root_path, 'static/favicon.ico', mimetype='image/vnd.microsoft.icon')

    @main_bp.route('/start-interview', methods=['POST'])
    def start_interview():
        data = request.get_json()
        topic = data.get('topic')

        if not topic:
            return jsonify({'error': 'Topic is required.'}), 400

        session = InterviewSession(topic)
        session.save(r)
        initial_question = session.generate_initial_question()
        session.save(r) # Save state after generating question
        
        if initial_question.startswith("Error:"):
            return jsonify({'error': initial_question}), 500
        
        return jsonify({'session_id': session.session_id, 'question': initial_question})

    @main_bp.route('/submit', methods=['POST'])
    def submit():
        data = request.get_json()
        session_id = data.get('session_id')
        answer = data.get('answer')

        if not r:
            return jsonify({'error': 'Database connection not available.', 'finished': True}), 500

        if not session_id:
            return jsonify({'error': 'Invalid session ID', 'finished': True}), 400

        current_session = InterviewSession.load(r, session_id)
        if not current_session:
            return jsonify({'error': 'Session expired or not found.', 'finished': True}), 404

        if current_session.question_count >= 3:
            # The last answer was for the final question. End of interview.
            if current_session.questions_and_answers:
                 current_session.questions_and_answers[-1]["answer"] = answer
            transcript = "\n".join([f"Q: {qa['question']}\nA: {qa['answer']}" for qa in current_session.questions_and_answers])
            print(f"--- FINAL TRANSCRIPT ---\n{transcript}")
            r.delete(f"session:{session_id}")
            return jsonify({'question': 'Thank you for your time! The interview is now complete.', 'finished': True})

        # Generate follow-up or leading question
        next_question = current_session.generate_next_question(answer)
        current_session.save(r) # Save state after generating question

        if next_question.startswith("Error:"):
            return jsonify({'error': next_question, 'finished': True}), 500
        
        return jsonify({'question': next_question, 'finished': False})

    app.register_blueprint(main_bp)
