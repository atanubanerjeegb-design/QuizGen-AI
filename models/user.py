from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from models import db

class User(db.Model, UserMixin):
    """User database model for authentication and role control."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    pdfs = db.relationship('PDF', backref='user', lazy=True, cascade='all, delete-orphan')
    results = db.relationship('Result', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hashes the password and sets password_hash."""
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        """Verifies password against stored password_hash."""
        return check_password_hash(self.password_hash, password)
        
    def __repr__(self):
        return f'<User {self.username}>'
