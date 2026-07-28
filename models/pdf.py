from datetime import datetime
from models import db

class PDF(db.Model):
    """Database model for storing uploaded PDF metadata."""
    __tablename__ = 'pdfs'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(512), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    
    # Relationships
    quizzes = db.relationship('Quiz', backref='pdf', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<PDF {self.filename}>'
