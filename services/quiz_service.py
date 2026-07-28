import json
from collections import defaultdict
from datetime import datetime, timedelta
from sqlalchemy import func
from models import db, Quiz, Question, Result, User

def grade_quiz(user_id, quiz_id, submitted_answers, time_taken=0):
    """
    Grades a user's quiz submission, saves the result, and returns the score info.
    """
    quiz = Quiz.query.get_or_404(quiz_id)
    questions = quiz.questions
    
    score = 0
    total_questions = len(questions)
    
    # Standardize keys to string for JSON serialization
    sanitized_answers = {}
    for q in questions:
        q_id_str = str(q.id)
        user_ans = submitted_answers.get(q_id_str, "").strip().upper()
        sanitized_answers[q_id_str] = user_ans
        if user_ans == q.correct_answer:
            score += 1
            
    percentage = (score / total_questions * 100) if total_questions > 0 else 0.0
    
    result = Result(
        user_id=user_id,
        quiz_id=quiz_id,
        score=score,
        total_questions=total_questions,
        percentage=round(percentage, 1),
        answers_json=json.dumps(sanitized_answers),
        attempted_at=datetime.utcnow(),
        time_taken=time_taken
    )
    
    db.session.add(result)
    db.session.commit()
    return result

def get_user_stats(user_id):
    """
    Computes comprehensive statistics for a given user.
    """
    results = Result.query.filter_by(user_id=user_id).all()
    
    total_quizzes = len(results)
    if total_quizzes == 0:
        return {
            "total_quizzes": 0,
            "average_score": 0,
            "high_score": 0,
            "strong_topics": ["None yet"],
            "weak_topics": ["None yet"],
            "total_correct": 0,
            "total_questions": 0
        }
        
    total_correct = sum(r.score for r in results)
    total_questions = sum(r.total_questions for r in results)
    average_score = round(sum(r.percentage for r in results) / total_quizzes, 1)
    high_score = round(max(r.percentage for r in results), 1)
    
    # Determine Strong and Weak Topics based on question text terms and answer success
    # Stopwords list to filter out common English words
    stopwords = {'what', 'which', 'where', 'whose', 'about', 'above', 'after', 'again', 'against', 
                 'other', 'there', 'their', 'these', 'those', 'under', 'while', 'would', 'could',
                 'should', 'first', 'second', 'third', 'based', 'provided', 'context', 'significance',
                 'represent', 'primary', 'mechanism', 'associated', 'variable', 'definition'}
                 
    topic_correct_count = defaultdict(int)
    topic_total_count = defaultdict(int)
    
    for r in results:
        try:
            answers = json.loads(r.answers_json)
        except Exception:
            continue
            
        quiz = Quiz.query.get(r.quiz_id)
        if not quiz:
            continue
            
        for q in quiz.questions:
            q_id_str = str(q.id)
            user_ans = answers.get(q_id_str, "")
            is_correct = (user_ans == q.correct_answer)
            
            # Simple keyword extraction as topic approximation
            # Extract nouns/keywords from question text
            words = [w.strip(".,;:?!()\"'").lower() for w in q.question_text.split() if len(w) > 4]
            # Filter stopwords and numeric values
            keywords = [w for w in words if w not in stopwords and w.isalpha()]
            
            for keyword in keywords[:3]:  # Take top 3 keywords per question
                topic_total_count[keyword] += 1
                if is_correct:
                    topic_correct_count[keyword] += 1
                    
    # Calculate performance ratio per topic
    topic_performance = {}
    for topic, total in topic_total_count.items():
        if total >= 1:  # Require at least 1 appearance
            correct = topic_correct_count[topic]
            ratio = correct / total
            topic_performance[topic] = (ratio, total)
            
    # Sort topics
    sorted_topics = sorted(topic_performance.items(), key=lambda x: (x[1][0], x[1][1]), reverse=True)
    
    strong_topics = [t[0].title() for t in sorted_topics if t[1][0] >= 0.7]
    weak_topics = [t[0].title() for t in reversed(sorted_topics) if t[1][0] < 0.6]
    
    if not strong_topics:
        strong_topics = ["Information Processing", "General Comprehension"]
    if not weak_topics:
        weak_topics = ["None identified"]
        
    return {
        "total_quizzes": total_quizzes,
        "average_score": average_score,
        "high_score": high_score,
        "strong_topics": strong_topics[:3],
        "weak_topics": weak_topics[:3],
        "total_correct": total_correct,
        "total_questions": total_questions
    }

def get_leaderboard(limit=10):
    """
    Generates leaderboard stats for top performers.
    """
    # Group results by user_id
    stats = db.session.query(
        Result.user_id,
        func.count(Result.id).label('quizzes_taken'),
        func.avg(Result.percentage).label('avg_score'),
        func.sum(Result.score).label('total_correct')
    ).group_by(Result.user_id).order_by(func.avg(Result.percentage).desc()).limit(limit).all()
    
    leaderboard = []
    for rank, row in enumerate(stats, 1):
        user = User.query.get(row.user_id)
        if user:
            leaderboard.append({
                "rank": rank,
                "username": user.username,
                "quizzes_taken": row.quizzes_taken,
                "avg_score": round(row.avg_score, 1),
                "total_points": row.total_correct * 10  # Arbitrary point system
            })
    return leaderboard

def get_activity_data(user_id, days=30):
    """
    Retrieves chronological quiz attempts data for charting.
    """
    cutoff = datetime.utcnow() - timedelta(days=days)
    results = Result.query.filter(Result.user_id == user_id, Result.attempted_at >= cutoff)\
                          .order_by(Result.attempted_at.asc()).all()
                          
    dates = []
    scores = []
    for r in results:
        dates.append(r.attempted_at.strftime("%b %d"))
        scores.append(r.percentage)
        
    return {
        "dates": dates,
        "scores": scores
    }
