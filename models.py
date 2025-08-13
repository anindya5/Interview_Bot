from extensions import db
from datetime import datetime

# Note: The db instance is now created in extensions.py
# and initialized in the app factory to avoid circular imports.

class Interview(db.Model):
    """Represents a single interview session."""
    id = db.Column(db.Integer, primary_key=True)
    candidate_name = db.Column(db.String(100), nullable=False)
    candidate_email = db.Column(db.String(100), nullable=False)
    topic = db.Column(db.String(100), nullable=False)
    average_score = db.Column(db.Float, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # This creates a one-to-many relationship with the Result model
    results = db.relationship('Result', backref='interview', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Interview {self.id} for {self.candidate_name}>'

class Result(db.Model):
    """Represents a single question-answer result within an interview."""
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    llm_answer = db.Column(db.Text, nullable=True)
    score = db.Column(db.Float, nullable=False)
    
    # This is the foreign key that links a result to a specific interview
    interview_id = db.Column(db.Integer, db.ForeignKey('interview.id'), nullable=False)

    def __repr__(self):
        return f'<Result {self.id} for Interview {self.interview_id}>'
