"""Learning platform — Quiz, Certificates, Assignments."""
import logging
from db import db
from models import _id, _now
from datetime import datetime, timezone

logger = logging.getLogger('getszy.learning')


# ── Quiz System ──────────────────────────────────────────────────────────────

async def create_quiz(course_slug: str, title: str, questions: list, time_limit_min: int = 30) -> dict:
    """Create a quiz for a course."""
    quiz = {
        'id': _id(),
        'course_slug': course_slug,
        'title': title,
        'questions': questions,  # [{question, options: [], correct_index, explanation}]
        'time_limit_min': time_limit_min,
        'total_questions': len(questions),
        'passing_score': 70,
        'created_at': _now(),
    }
    await db.quizzes.insert_one(quiz)
    return quiz


async def get_quiz(quiz_id: str) -> dict:
    """Get quiz (without answers)."""
    quiz = await db.quizzes.find_one({'id': quiz_id}, {'_id': 0})
    if not quiz:
        return {'error': 'Quiz not found'}
    # Hide correct answers
    for q in quiz.get('questions', []):
        q.pop('correct_index', None)
        q.pop('explanation', None)
    return quiz


async def submit_quiz(quiz_id: str, user_id: str, answers: list) -> dict:
    """Submit quiz answers and calculate score."""
    quiz = await db.quizzes.find_one({'id': quiz_id}, {'_id': 0})
    if not quiz:
        return {'error': 'Quiz not found'}

    questions = quiz.get('questions', [])
    correct = 0
    results = []
    for i, q in enumerate(questions):
        user_answer = answers[i] if i < len(answers) else -1
        is_correct = user_answer == q.get('correct_index', -1)
        if is_correct:
            correct += 1
        results.append({
            'question': q['question'],
            'correct': is_correct,
            'correct_answer': q.get('correct_index', -1),
            'explanation': q.get('explanation', ''),
        })

    score = round(correct / max(len(questions), 1) * 100, 1)
    passed = score >= quiz.get('passing_score', 70)

    attempt = {
        'id': _id(),
        'quiz_id': quiz_id,
        'user_id': user_id,
        'answers': answers,
        'score': score,
        'correct_count': correct,
        'total_questions': len(questions),
        'passed': passed,
        'submitted_at': _now(),
    }
    await db.quiz_attempts.insert_one(attempt)

    return {
        'score': score,
        'passed': passed,
        'correct_count': correct,
        'total_questions': len(questions),
        'passing_score': quiz.get('passing_score', 70),
        'results': results,
    }


# ── Certificates ─────────────────────────────────────────────────────────────

async def generate_certificate(user_id: str, course_slug: str, user_name: str, course_title: str) -> dict:
    """Generate a course completion certificate."""
    cert_id = _id()
    certificate = {
        'id': cert_id,
        'user_id': user_id,
        'course_slug': course_slug,
        'user_name': user_name,
        'course_title': course_title,
        'issued_at': _now(),
        'certificate_url': f'/certificates/{cert_id}',
        'verification_code': cert_id[:8].upper(),
    }
    await db.certificates.insert_one(certificate)
    return certificate


async def get_user_certificates(user_id: str) -> list:
    """Get all certificates for a user."""
    cursor = db.certificates.find({'user_id': user_id}, {'_id': 0}).sort('issued_at', -1)
    return await cursor.to_list(100)


async def verify_certificate(verification_code: str) -> dict:
    """Verify a certificate by its code."""
    cert = await db.certificates.find_one(
        {'verification_code': verification_code.upper()},
        {'_id': 0}
    )
    if not cert:
        return {'valid': False, 'error': 'Certificate not found'}
    return {'valid': True, 'certificate': cert}


# ── Assignments ──────────────────────────────────────────────────────────────

async def create_assignment(course_slug: str, title: str, description: str, deadline: str = None) -> dict:
    assignment = {
        'id': _id(),
        'course_slug': course_slug,
        'title': title,
        'description': description,
        'deadline': deadline,
        'submissions': [],
        'created_at': _now(),
    }
    await db.assignments.insert_one(assignment)
    return assignment


async def submit_assignment(assignment_id: str, user_id: str, content: str, file_url: str = None) -> dict:
    assignment = await db.assignments.find_one({'id': assignment_id})
    if not assignment:
        return {'error': 'Assignment not found'}

    submission = {
        'user_id': user_id,
        'content': content,
        'file_url': file_url,
        'status': 'submitted',
        'submitted_at': _now(),
    }
    await db.assignments.update_one(
        {'id': assignment_id},
        {'$push': {'submissions': submission}}
    )
    return submission


async def grade_assignment(assignment_id: str, user_id: str, grade: str, feedback: str = '') -> dict:
    await db.assignments.update_one(
        {'id': assignment_id, 'submissions.user_id': user_id},
        {'$set': {
            'submissions.$.grade': grade,
            'submissions.$.feedback': feedback,
            'submissions.$.status': 'graded',
            'submissions.$.graded_at': _now(),
        }}
    )
    return {'ok': True, 'grade': grade}
