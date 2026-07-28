import os
from functools import wraps
from flask import render_template, redirect, url_for, flash, abort, request, current_app
from flask_login import login_required, current_user
from routes import admin_bp
from models import db, User, PDF, Quiz, Result

def admin_required(f):
    """Decorator to restrict access to administrator accounts only."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/', methods=['GET'])
@login_required
@admin_required
def dashboard():
    """Render admin control panel with site statistics and table managers."""
    users = User.query.order_by(User.id.asc()).all()
    pdfs = PDF.query.order_by(PDF.upload_date.desc()).all()
    quizzes = Quiz.query.order_by(Quiz.created_at.desc()).all()
    
    # Calculate global analytics
    total_users = User.query.count()
    total_pdfs = PDF.query.count()
    total_quizzes = Quiz.query.count()
    total_results = Result.query.count()
    
    avg_score_raw = db.session.query(db.func.avg(Result.percentage)).scalar()
    avg_score = round(avg_score_raw, 1) if avg_score_raw is not None else 0.0
    
    analytics = {
        "total_users": total_users,
        "total_pdfs": total_pdfs,
        "total_quizzes": total_quizzes,
        "total_results": total_results,
        "avg_score": avg_score
    }
    
    return render_template(
        'admin.html',
        users=users,
        pdfs=pdfs,
        quizzes=quizzes,
        analytics=analytics
    )

@admin_bp.route('/user/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user account and cascade delete their data."""
    if user_id == current_user.id:
        flash("You cannot delete your own admin account.", "danger")
        return redirect(url_for('admin.dashboard'))
        
    user = User.query.get_or_404(user_id)
    
    # Loop through and remove physical files for PDF records associated with user
    for pdf in user.pdfs:
        if os.path.exists(pdf.filepath):
            try:
                os.remove(pdf.filepath)
            except Exception as e:
                current_app.logger.error(f"Failed to delete file {pdf.filepath}: {str(e)}")
                
    db.session.delete(user)
    db.session.commit()
    flash(f"User '{user.username}' has been successfully deleted.", "success")
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/user/<int:user_id>/toggle_admin', methods=['POST'])
@login_required
@admin_required
def toggle_admin(user_id):
    """Toggle administrator permissions for a user account."""
    if user_id == current_user.id:
        flash("You cannot revoke your own admin rights.", "danger")
        return redirect(url_for('admin.dashboard'))
        
    user = User.query.get_or_404(user_id)
    user.is_admin = not user.is_admin
    db.session.commit()
    role = "Administrator" if user.is_admin else "User"
    flash(f"Role for '{user.username}' changed to {role}.", "success")
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/pdf/<int:pdf_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_pdf(pdf_id):
    """Delete a PDF file record and delete the physical file from disk."""
    pdf = PDF.query.get_or_404(pdf_id)
    
    # Remove physical file
    if os.path.exists(pdf.filepath):
        try:
            os.remove(pdf.filepath)
        except Exception as e:
            current_app.logger.error(f"Failed to remove file from disk: {str(e)}")
            
    db.session.delete(pdf)
    db.session.commit()
    flash(f"PDF metadata and file '{pdf.filename}' deleted.", "success")
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/quiz/<int:quiz_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_quiz(quiz_id):
    """Delete a quiz, removing its questions and attempt results."""
    quiz = Quiz.query.get_or_404(quiz_id)
    db.session.delete(quiz)
    db.session.commit()
    flash(f"Quiz '{quiz.title}' and associated questions deleted.", "success")
    return redirect(url_for('admin.dashboard'))
