from datetime import datetime
from models import db

class Quiz(db.Model):
    """Database model for generated quizzes."""
    __tablename__ = 'quizzes'
    
    id = db.Column(db.Integer, primary_key=True)
    pdf_id = db.Column(db.Integer, db.ForeignKey('pdfs.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    difficulty = db.Column(db.String(50), nullable=False)  # Easy, Medium, Hard
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    questions = db.relationship('Question', backref='quiz', lazy=True, cascade='all, delete-orphan')
    results = db.relationship('Result', backref='quiz', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Quiz {self.title}>'
