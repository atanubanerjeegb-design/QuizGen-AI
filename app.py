import os
from flask import Flask, render_template
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import Config
from models import db, User
from routes import auth_bp, main_bp, quiz_bp, admin_bp

# Initialize CSRF protection globally
csrf = CSRFProtect()

def create_app(config_class=Config):
    """Flask Application Factory."""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize DB
    db.init_app(app)
    
    # Initialize CSRF Protection
    csrf.init_app(app)
    
    # Configure Login Manager
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
        
    # Register blueprints
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)
    app.register_blueprint(quiz_bp, url_prefix='/quiz')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    # Styled Error Pages
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('layout.html', error_code=403, error_title="Access Forbidden", error_desc="You do not have administrative permissions to view this resource."), 403
        
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('layout.html', error_code=404, error_title="Page Not Found", error_desc="The page you are looking for does not exist or has been relocated."), 404
        
    # Initialize database tables and folders
    with app.app_context():
        db.create_all()
        # Verify and create upload folder
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=app.config.get('DEBUG', True))
