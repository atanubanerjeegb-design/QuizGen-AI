from datetime import datetime
from models import db

class Result(db.Model):
    """Database model for storing quiz scores and attempts."""
    __tablename__ = 'results'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id', ondelete='CASCADE'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    percentage = db.Column(db.Float, nullable=False)
    attempted_at = db.Column(db.DateTime, default=datetime.utcnow)
    answers_json = db.Column(db.Text, nullable=False)  # Stores JSON string of answers: e.g. {"1": "A", "2": "C"}
    time_taken = db.Column(db.Integer, nullable=True, default=0) # Time taken in seconds
    
    def __repr__(self):
        return f'<Result {self.id} User {self.user_id} Quiz {self.quiz_id} Score {self.score}/{self.total_questions}>'
