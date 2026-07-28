import os
from flask import render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from routes import main_bp
from models import db, PDF, Quiz, Question, Result
from services.pdf_service import extract_pdf_content
from services.ai_service import generate_quiz_questions
from services.quiz_service import get_user_stats, get_leaderboard, get_activity_data

def allowed_file(filename):
    """Checks if the uploaded file has a valid PDF extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@main_bp.route('/')
def index():
    """Render index landing page."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Render user dashboard with statistics, history, charts, and leaderboard."""
    user_pdfs = PDF.query.filter_by(user_id=current_user.id).order_by(PDF.upload_date.desc()).all()
    
    # Get all quizzes related to user's PDFs
    pdf_ids = [pdf.id for pdf in user_pdfs]
    recent_quizzes = []
    if pdf_ids:
        recent_quizzes = Quiz.query.filter(Quiz.pdf_id.in_(pdf_ids)).order_by(Quiz.created_at.desc()).all()
        
    stats = get_user_stats(current_user.id)
    leaderboard = get_leaderboard(limit=5)
    activity = get_activity_data(current_user.id, days=30)
    
    return render_template(
        'dashboard.html',
        pdfs=user_pdfs,
        quizzes=recent_quizzes,
        stats=stats,
        leaderboard=leaderboard,
        activity_dates=activity["dates"],
        activity_scores=activity["scores"]
    )

def create_quiz_from_pdf(pdf_record, difficulty, num_questions):
    """Helper to orchestrate quiz generation from a PDF record."""
    # 1. Parse and extract PDF content (or read cache)
    parsed_data = extract_pdf_content(pdf_record.filepath)
    extracted_text = parsed_data.get("text", "")
    
    if not extracted_text or len(extracted_text.strip()) < 50:
        raise ValueError("The PDF does not contain sufficient text. Ensure it is not password-protected or empty.")
        
    # 2. Query previous questions for this PDF to prevent duplicates
    existing_questions = db.session.query(Question.question_text).join(Quiz).filter(Quiz.pdf_id == pdf_record.id).all()
    excluded_questions = [q[0] for q in existing_questions]
    
    # 3. Generate questions
    quiz_data = generate_quiz_questions(
        parsed_data, 
        difficulty, 
        num_questions, 
        pdf_record.filename,
        excluded_questions=excluded_questions
    )
    
    if not quiz_data or "questions" not in quiz_data or len(quiz_data["questions"]) == 0:
        raise ValueError("Failed to generate questions. The AI service timed out or returned invalid format.")
        
    # 4. Create Quiz record
    quiz_record = Quiz(
        pdf_id=pdf_record.id,
        title=quiz_data["title"],
        difficulty=difficulty
    )
    db.session.add(quiz_record)
    db.session.commit()  # Commit to get quiz_record.id
    
    # 5. Save question records
    for idx, q in enumerate(quiz_data["questions"]):
        question_record = Question(
            quiz_id=quiz_record.id,
            question_text=q["question"],
            option_a=q["option_a"],
            option_b=q["option_b"],
            option_c=q["option_c"],
            option_d=q["option_d"],
            correct_answer=q["correct_answer"].strip().upper(),
            explanation=q["explanation"],
            topic=q.get("topic", "General"),
            difficulty=q.get("difficulty", difficulty)
        )
        db.session.add(question_record)
        
    db.session.commit()
    return quiz_record

@main_bp.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """Handle PDF upload, text parsing, and AI quiz generation."""
    if request.method == 'POST':
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file part in request."}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({"success": False, "error": "No file selected."}), 400
            
        if not allowed_file(file.filename):
            return jsonify({"success": False, "error": "Invalid file type. Only PDF uploads are supported."}), 400
            
        try:
            difficulty = request.form.get('difficulty', 'Medium').capitalize()
            if difficulty not in ['Easy', 'Medium', 'Hard']:
                difficulty = 'Medium'
                
            num_questions_str = request.form.get('num_questions', '5')
            try:
                num_questions = int(num_questions_str)
                if num_questions not in current_app.config['QUIZ_QUESTION_OPTIONS']:
                    num_questions = current_app.config['DEFAULT_QUESTION_COUNT']
            except ValueError:
                num_questions = current_app.config['DEFAULT_QUESTION_COUNT']
                
            upload_dir = current_app.config['UPLOAD_FOLDER']
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir, exist_ok=True)
                
            orig_filename = secure_filename(file.filename)
            filename = f"user_{current_user.id}_{orig_filename}"
            filepath = os.path.join(upload_dir, filename)
            
            # Stream/save file to disk
            file.save(filepath)
            
            # Create PDF record
            pdf_record = PDF(
                filename=orig_filename,
                filepath=filepath,
                user_id=current_user.id
            )
            db.session.add(pdf_record)
            db.session.commit()
            
            try:
                quiz_record = create_quiz_from_pdf(pdf_record, difficulty, num_questions)
            except Exception as quiz_err:
                db.session.delete(pdf_record)
                db.session.commit()
                if os.path.exists(filepath):
                    os.remove(filepath)
                raise quiz_err
                
            return jsonify({
                "success": True,
                "quiz_id": quiz_record.id,
                "redirect_url": url_for('quiz.take_quiz', quiz_id=quiz_record.id)
            })
            
        except Exception as err:
            current_app.logger.error(f"Upload and quiz generation failed: {str(err)}")
            return jsonify({"success": False, "error": f"An error occurred: {str(err)}"}), 500
            
    return render_template('upload.html')

@main_bp.route('/pdf/<int:pdf_id>/generate', methods=['POST'])
@login_required
def generate_quiz_from_existing_pdf(pdf_id):
    """Generate a brand new quiz from an already uploaded PDF, ensuring distinct questions."""
    pdf_record = PDF.query.get_or_404(pdf_id)
    if pdf_record.user_id != current_user.id and not current_user.is_admin:
        return jsonify({"success": False, "error": "Not authorized."}), 403
        
    try:
        difficulty = request.form.get('difficulty', 'Medium').capitalize()
        if difficulty not in ['Easy', 'Medium', 'Hard']:
            difficulty = 'Medium'
            
        num_questions_str = request.form.get('num_questions', '5')
        try:
            num_questions = int(num_questions_str)
            if num_questions not in current_app.config['QUIZ_QUESTION_OPTIONS']:
                num_questions = current_app.config['DEFAULT_QUESTION_COUNT']
        except ValueError:
            num_questions = current_app.config['DEFAULT_QUESTION_COUNT']
            
        # Generate the new quiz from existing PDF content
        quiz_record = create_quiz_from_pdf(pdf_record, difficulty, num_questions)
        
        # Check if requested as AJAX or standard form submit
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accept_mimetypes.accept_json:
            return jsonify({
                "success": True,
                "quiz_id": quiz_record.id,
                "redirect_url": url_for('quiz.take_quiz', quiz_id=quiz_record.id)
            })
        else:
            flash(f"New quiz '{quiz_record.title}' generated successfully!", "success")
            return redirect(url_for('quiz.take_quiz', quiz_id=quiz_record.id))
            
    except Exception as err:
        current_app.logger.error(f"Existing PDF quiz generation failed: {str(err)}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.accept_mimetypes.accept_json:
            return jsonify({"success": False, "error": str(err)}), 500
        else:
            flash(f"Failed to generate quiz: {str(err)}", "danger")
            return redirect(url_for('main.dashboard'))
