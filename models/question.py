from models import db

class Question(db.Model):
    """Database model for storing individual quiz questions."""
    __tablename__ = 'questions'
    
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quizzes.id', ondelete='CASCADE'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(255), nullable=False)
    option_b = db.Column(db.String(255), nullable=False)
    option_c = db.Column(db.String(255), nullable=False)
    option_d = db.Column(db.String(255), nullable=False)
    correct_answer = db.Column(db.String(1), nullable=False)  # A, B, C, or D
    explanation = db.Column(db.Text, nullable=False)
    topic = db.Column(db.String(255), nullable=True)
    difficulty = db.Column(db.String(50), nullable=True)
    
    def __repr__(self):
        return f'<Question {self.id} on Quiz {self.quiz_id}>'
