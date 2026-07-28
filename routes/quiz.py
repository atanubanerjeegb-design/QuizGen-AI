import json
from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from routes import quiz_bp
from models import db, Quiz, Question, Result
from services.quiz_service import grade_quiz

@quiz_bp.route('/<int:quiz_id>', methods=['GET'])
@login_required
def take_quiz(quiz_id):
    """Render the quiz-taking interface with questions (hiding answers and explanations)."""
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = quiz.questions
    
    if not questions:
        flash("This quiz doesn't have any questions.", "warning")
        return redirect(url_for('main.dashboard'))
        
    return render_template('quiz.html', quiz=quiz, questions=questions)

@quiz_bp.route('/<int:quiz_id>/submit', methods=['POST'])
@login_required
def submit_quiz(quiz_id):
    """Receive answers JSON, grade the quiz, and return result redirect info."""
    quiz = Quiz.query.get_or_404(quiz_id)
    
    data = request.get_json()
    if not data or 'answers' not in data:
        return jsonify({"success": False, "error": "No answers submitted."}), 400
        
    submitted_answers = data['answers']  # Dict: {"question_id_str": "A/B/C/D"}
    time_spent = int(data.get('time_spent', 0))
    
    try:
        # Grade quiz and save to Result table (including time_spent)
        result = grade_quiz(current_user.id, quiz.id, submitted_answers, time_taken=time_spent)
        
        return jsonify({
            "success": True,
            "result_id": result.id,
            "redirect_url": url_for('quiz.view_result', result_id=result.id)
        })
    except Exception as e:
        return jsonify({"success": False, "error": f"Failed to grade quiz: {str(e)}"}), 500

@quiz_bp.route('/result/<int:result_id>', methods=['GET'])
@login_required
def view_result(result_id):
    """Render the detailed results page showing scores, answers, and explanations."""
    result = Result.query.get_or_404(result_id)
    
    if result.user_id != current_user.id and not current_user.is_admin:
        flash("You are not authorized to view this result.", "danger")
        return redirect(url_for('main.dashboard'))
        
    quiz = Quiz.query.get(result.quiz_id)
    if not quiz:
        flash("The corresponding quiz has been deleted.", "danger")
        return redirect(url_for('main.dashboard'))
        
    try:
        user_answers = json.loads(result.answers_json)
    except Exception:
        user_answers = {}
        
    quiz_questions = quiz.questions
    review_data = []
    
    # Calculate Strong and Weak Topics specifically for this attempt
    topic_stats = {}  # topic -> {correct: 0, total: 0}
    
    for q in quiz_questions:
        u_ans = user_answers.get(str(q.id), "").strip().upper()
        is_correct = (u_ans == q.correct_answer)
        review_data.append({
            "question": q,
            "user_answer": u_ans,
            "is_correct": is_correct
        })
        
        topic = q.topic or "General Concepts"
        if topic not in topic_stats:
            topic_stats[topic] = {"correct": 0, "total": 0}
        topic_stats[topic]["total"] += 1
        if is_correct:
            topic_stats[topic]["correct"] += 1

    strong_topics = []
    weak_topics = []
    for topic, stats in topic_stats.items():
        ratio = stats["correct"] / stats["total"]
        if ratio >= 0.75:
            strong_topics.append(topic)
        else:
            weak_topics.append(topic)
            
    # Format time taken
    seconds = result.time_taken or 0
    mins = seconds // 60
    secs = seconds % 60
    time_taken_formatted = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
    
    return render_template(
        'result.html',
        result=result,
        quiz=quiz,
        review_data=review_data,
        time_taken_formatted=time_taken_formatted,
        strong_topics=strong_topics,
        weak_topics=weak_topics
    )

@quiz_bp.route('/history', methods=['GET'])
@login_required
def history():
    """Render the chronological quiz history list for the user."""
    results = Result.query.filter_by(user_id=current_user.id).order_by(Result.attempted_at.desc()).all()
    return render_template('profile.html', history=results)
