"""Learning extras — quiz system, certificates, assignments."""
import uuid
import hashlib
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from db import db


def _now():
    return datetime.now(timezone.utc).isoformat()


async def create_quiz(course_id: str, questions: List[Dict], passing_score: int = 70):
    quiz = {
        'id': str(uuid.uuid4()), 'course_id': course_id,
        'questions': questions, 'passing_score': passing_score,
        'created_at': _now()
    }
    await db.quizzes.insert_one(quiz)
    quiz.pop('_id', None)
    return quiz


async def submit_quiz(quiz_id: str, user_id: str, answers: List[int]):
    quiz = await db.quizzes.find_one({'id': quiz_id})
    if not quiz:
        return {'error': 'Quiz not found'}
    correct = 0
    for i, q in enumerate(quiz.get('questions', [])):
        if i < len(answers) and answers[i] == q.get('correct'):
            correct += 1
    total = len(quiz.get('questions', []))
    score = round(correct / total * 100, 1) if total else 0
    passed = score >= quiz.get('passing_score', 70)
    result = {
        'id': str(uuid.uuid4()), 'quiz_id': quiz_id, 'user_id': user_id,
        'answers': answers, 'score': score, 'passed': passed,
        'submitted_at': _now()
    }
    await db.quiz_results.insert_one(result)
    if passed:
        cert = await issue_certificate(user_id, quiz.get('course_id', ''), score)
        result['certificate'] = cert
    result.pop('_id', None)
    return result


async def issue_certificate(user_id: str, course_id: str, score: float = 100):
    cert_id = str(uuid.uuid4())
    verify_hash = hashlib.sha256(f'{cert_id}:{user_id}:{course_id}'.encode()).hexdigest()[:16]
    cert = {
        'id': cert_id, 'user_id': user_id, 'course_id': course_id,
        'score': score, 'verify_hash': verify_hash,
        'issued_at': _now()
    }
    await db.certificates.insert_one(cert)
    cert.pop('_id', None)
    return cert


async def verify_certificate(cert_id: str, verify_hash: str) -> bool:
    cert = await db.certificates.find_one({'id': cert_id, 'verify_hash': verify_hash})
    return cert is not None


async def get_user_certificates(user_id: str):
    cur = db.certificates.find({'user_id': user_id}, {'_id': 0}).sort('issued_at', -1)
    return [c async for c in cur]


async def create_assignment(course_id: str, title: str, description: str, due_date: str = ''):
    assignment = {
        'id': str(uuid.uuid4()), 'course_id': course_id,
        'title': title, 'description': description,
        'due_date': due_date, 'submissions': [],
        'created_at': _now()
    }
    await db.assignments.insert_one(assignment)
    assignment.pop('_id', None)
    return assignment


async def submit_assignment(assignment_id: str, user_id: str, content: str):
    assignment = await db.assignments.find_one({'id': assignment_id})
    if not assignment:
        return {'error': 'Assignment not found'}
    submission = {
        'id': str(uuid.uuid4()), 'user_id': user_id,
        'content': content, 'submitted_at': _now(), 'grade': None
    }
    await db.assignments.update_one({'id': assignment_id}, {'$push': {'submissions': submission}})
    return submission


async def grade_assignment(assignment_id: str, submission_id: str, grade: str, feedback: str = ''):
    assignment = await db.assignments.find_one({'id': assignment_id})
    if not assignment:
        return {'error': 'Assignment not found'}
    for sub in assignment.get('submissions', []):
        if sub['id'] == submission_id:
            sub['grade'] = grade
            sub['feedback'] = feedback
            await db.assignments.update_one({'id': assignment_id}, {'$set': {'submissions': assignment['submissions']}})
            return {'status': 'graded', 'grade': grade}
    return {'error': 'Submission not found'}
