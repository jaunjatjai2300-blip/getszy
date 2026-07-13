import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from auth import get_current_user, get_current_admin
from db import db

router = APIRouter(prefix='/admin/learning-platform', tags=['learning-platform'])


def _now():
    return datetime.now(timezone.utc).isoformat()


class ModuleIn(BaseModel):
    title: str
    description: str = ''
    order: int = 0
    lessons: List[dict] = []
    duration_minutes: int = 0


class ModuleReorderIn(BaseModel):
    module_ids: List[str]


class QuestionIn(BaseModel):
    question: str
    type: str
    options: List[str] = []
    correct_answer: Any = ''
    points: int = 1
    explanation: str = ''


class QuizIn(BaseModel):
    course_id: str
    module_id: str = ''
    title: str
    questions: List[QuestionIn]
    time_limit_minutes: int = 30
    passing_score: float = 70
    max_attempts: int = 3


class QuizSubmitIn(BaseModel):
    user_id: str
    answers: List[dict]
    time_taken: int = 0


class CertificateTemplateIn(BaseModel):
    course_id: str
    title: str
    template_html: str = ''
    badge_image_url: str = ''
    issuer_name: str = 'Getszy AI'
    valid_days: int = 365


class CertificateIssueIn(BaseModel):
    user_id: str
    course_id: str


class AssignmentIn(BaseModel):
    course_id: str
    module_id: str = ''
    title: str
    description: str = ''
    type: str = 'essay'
    max_points: int = 100
    deadline: str = ''
    rubric: str = ''


class AssignmentSubmitIn(BaseModel):
    user_id: str
    file_url: str = ''
    notes: str = ''


class AssignmentGradeIn(BaseModel):
    score: float
    feedback: str = ''
    graded_by: str = ''


class LearningPathIn(BaseModel):
    title: str
    description: str = ''
    courses: List[str] = []
    difficulty: str = 'beginner'
    estimated_hours: int = 0


# ===== Course Modules =====

@router.post('/courses/{course_id}/modules')
async def add_module(course_id: str, body: ModuleIn, _=Depends(get_current_admin)):
    course = await db.courses.find_one({'id': course_id}, {'_id': 0})
    if not course:
        raise HTTPException(404, 'Course not found')
    module_id = str(uuid.uuid4())
    doc = {
        'id': module_id,
        'course_id': course_id,
        **body.model_dump(),
        'created_at': _now(),
        'updated_at': _now(),
    }
    await db.lp_modules.insert_one(doc)
    doc.pop('_id', None)
    return doc


@router.put('/courses/{course_id}/modules/{module_id}')
async def update_module(course_id: str, module_id: str, body: dict, _=Depends(get_current_admin)):
    body.pop('id', None)
    body.pop('course_id', None)
    body['updated_at'] = _now()
    await db.lp_modules.update_one({'id': module_id, 'course_id': course_id}, {'$set': body})
    module = await db.lp_modules.find_one({'id': module_id, 'course_id': course_id}, {'_id': 0})
    if not module:
        raise HTTPException(404, 'Module not found')
    return module


@router.delete('/courses/{course_id}/modules/{module_id}')
async def remove_module(course_id: str, module_id: str, _=Depends(get_current_admin)):
    result = await db.lp_modules.delete_one({'id': module_id, 'course_id': course_id})
    if result.deleted_count == 0:
        raise HTTPException(404, 'Module not found')
    await db.lp_quizzes.delete_many({'module_id': module_id})
    await db.lp_assignments.delete_many({'module_id': module_id})
    return {'deleted': True}


@router.post('/courses/{course_id}/modules/reorder')
async def reorder_modules(course_id: str, body: ModuleReorderIn, _=Depends(get_current_admin)):
    for idx, mid in enumerate(body.module_ids):
        await db.lp_modules.update_one({'id': mid, 'course_id': course_id}, {'$set': {'order': idx}})
    modules = await db.lp_modules.find({'course_id': course_id}, {'_id': 0}).sort('order', 1).to_list(200)
    return {'modules': modules}


# ===== Quizzes =====

@router.post('/quizzes')
async def create_quiz(body: QuizIn, _=Depends(get_current_admin)):
    quiz_id = str(uuid.uuid4())
    questions = []
    for q in body.questions:
        questions.append({
            'id': str(uuid.uuid4()),
            **q.model_dump(),
        })
    doc = {
        'id': quiz_id,
        'course_id': body.course_id,
        'module_id': body.module_id,
        'title': body.title,
        'questions': questions,
        'time_limit_minutes': body.time_limit_minutes,
        'passing_score': body.passing_score,
        'max_attempts': body.max_attempts,
        'created_at': _now(),
    }
    await db.lp_quizzes.insert_one(doc)
    doc.pop('_id', None)
    return doc


@router.get('/quizzes')
async def list_quizzes(course_id: Optional[str] = None, module_id: Optional[str] = None, _=Depends(get_current_admin)):
    q: dict = {}
    if course_id:
        q['course_id'] = course_id
    if module_id:
        q['module_id'] = module_id
    quizzes = await db.lp_quizzes.find(q, {'_id': 0}).to_list(200)
    return quizzes


@router.get('/quizzes/{quiz_id}')
async def get_quiz(quiz_id: str, user=Depends(get_current_user)):
    quiz = await db.lp_quizzes.find_one({'id': quiz_id}, {'_id': 0})
    if not quiz:
        raise HTTPException(404, 'Quiz not found')
    if user.get('role') != 'admin':
        for q in quiz.get('questions', []):
            q.pop('correct_answer', None)
    return quiz


@router.post('/quizzes/{quiz_id}/submit')
async def submit_quiz(quiz_id: str, body: QuizSubmitIn, _=Depends(get_current_admin)):
    quiz = await db.lp_quizzes.find_one({'id': quiz_id}, {'_id': 0})
    if not quiz:
        raise HTTPException(404, 'Quiz not found')
    attempts = await db.quiz_submissions.count_documents({'quiz_id': quiz_id, 'user_id': body.user_id})
    if attempts >= quiz.get('max_attempts', 3):
        raise HTTPException(400, 'Max attempts reached')
    total_points = 0
    earned_points = 0
    results = []
    question_map = {q['id']: q for q in quiz.get('questions', [])}
    for ans in body.answers:
        qid = ans.get('question_id')
        given = ans.get('answer')
        q_data = question_map.get(qid)
        if not q_data:
            results.append({'question_id': qid, 'correct': False, 'points': 0})
            continue
        total_points += q_data.get('points', 1)
        is_correct = str(given).strip().lower() == str(q_data.get('correct_answer', '')).strip().lower()
        pts = q_data.get('points', 1) if is_correct else 0
        earned_points += pts
        results.append({'question_id': qid, 'correct': is_correct, 'points': pts})
    score = round((earned_points / total_points * 100) if total_points > 0 else 0, 2)
    passed = score >= quiz.get('passing_score', 70)
    submission_id = str(uuid.uuid4())
    doc = {
        'id': submission_id,
        'quiz_id': quiz_id,
        'user_id': body.user_id,
        'course_id': quiz.get('course_id', ''),
        'answers': body.answers,
        'results': results,
        'score': score,
        'passed': passed,
        'total_points': total_points,
        'earned_points': earned_points,
        'time_taken': body.time_taken,
        'submitted_at': _now(),
    }
    await db.quiz_submissions.insert_one(doc)
    doc.pop('_id', None)
    return doc


@router.get('/quizzes/{quiz_id}/results')
async def quiz_results(quiz_id: str, _=Depends(get_current_admin)):
    quiz = await db.lp_quizzes.find_one({'id': quiz_id}, {'_id': 0})
    if not quiz:
        raise HTTPException(404, 'Quiz not found')
    submissions = await db.quiz_submissions.find({'quiz_id': quiz_id}, {'_id': 0}).sort('submitted_at', -1).to_list(500)
    return {'quiz': quiz, 'submissions': submissions, 'total_submissions': len(submissions)}


# ===== Certificates =====

@router.post('/certificates')
async def create_certificate_template(body: CertificateTemplateIn, _=Depends(get_current_admin)):
    cert_id = str(uuid.uuid4())
    doc = {
        'id': cert_id,
        **body.model_dump(),
        'created_at': _now(),
    }
    await db.certificate_templates.insert_one(doc)
    doc.pop('_id', None)
    return doc


@router.post('/certificates/issue')
async def issue_certificate(body: CertificateIssueIn, _=Depends(get_current_admin)):
    user = await db.users.find_one({'id': body.user_id}, {'_id': 0, 'password_hash': 0})
    if not user:
        raise HTTPException(404, 'User not found')
    course = await db.courses.find_one({'id': body.course_id}, {'_id': 0})
    if not course:
        raise HTTPException(404, 'Course not found')
    modules = await db.lp_modules.find({'course_id': body.course_id}, {'_id': 0}).to_list(200)
    enrollment = await db.enrollments.find_one({'user_id': body.user_id, 'course_slug': course.get('slug', '')}, {'_id': 0})
    if not enrollment:
        raise HTTPException(400, 'User not enrolled in course')
    completed_modules = set(enrollment.get('completed_lessons', []))
    total_modules = len(modules)
    if total_modules > 0 and len(completed_modules) < total_modules and enrollment.get('progress', 0) < 1.0:
        raise HTTPException(400, 'Course not yet completed')
    quizzes = await db.lp_quizzes.find({'course_id': body.course_id}, {'_id': 0}).to_list(100)
    for quiz in quizzes:
        best = await db.quiz_submissions.find_one(
            {'quiz_id': quiz['id'], 'user_id': body.user_id, 'passed': True},
            sort=[('score', -1)],
        )
        if not best and quizzes:
            raise HTTPException(400, f'Quiz not passed: {quiz.get("title", quiz["id"])}')
    template = await db.certificate_templates.find_one({'course_id': body.course_id}, {'_id': 0})
    valid_days = template.get('valid_days', 365) if template else 365
    issued_at = datetime.now(timezone.utc)
    expires_at = issued_at.replace(year=issued_at.year + (valid_days // 365), month=issued_at.month + ((valid_days % 365) // 30), day=min(28, issued_at.day))
    cert_id = str(uuid.uuid4())
    doc = {
        'id': cert_id,
        'user_id': body.user_id,
        'user_name': user.get('name', ''),
        'course_id': body.course_id,
        'course_title': course.get('title', ''),
        'issued_at': issued_at.isoformat(),
        'expires_at': expires_at.isoformat(),
        'verification_url': f'/admin/learning-platform/certificates/{cert_id}/verify',
        'template_id': template.get('id', '') if template else '',
    }
    await db.certificates.insert_one(doc)
    doc.pop('_id', None)
    return doc


@router.get('/certificates')
async def list_certificates(user_id: Optional[str] = None, course_id: Optional[str] = None, _=Depends(get_current_admin)):
    q: dict = {}
    if user_id:
        q['user_id'] = user_id
    if course_id:
        q['course_id'] = course_id
    certs = await db.certificates.find(q, {'_id': 0}).sort('issued_at', -1).to_list(200)
    return certs


@router.get('/certificates/{cert_id}/verify')
async def verify_certificate(cert_id: str):
    cert = await db.certificates.find_one({'id': cert_id}, {'_id': 0})
    if not cert:
        raise HTTPException(404, 'Certificate not found')
    now = datetime.now(timezone.utc)
    expires = datetime.fromisoformat(cert.get('expires_at', '2099-01-01T00:00:00+00:00'))
    is_valid = now < expires
    return {
        'valid': is_valid,
        'holder_name': cert.get('user_name', ''),
        'course_title': cert.get('course_title', ''),
        'issued_at': cert.get('issued_at', ''),
        'expires_at': cert.get('expires_at', ''),
    }


# ===== Assignments =====

@router.post('/assignments')
async def create_assignment(body: AssignmentIn, _=Depends(get_current_admin)):
    assignment_id = str(uuid.uuid4())
    doc = {
        'id': assignment_id,
        **body.model_dump(),
        'created_at': _now(),
    }
    await db.lp_assignments.insert_one(doc)
    doc.pop('_id', None)
    return doc


@router.get('/assignments')
async def list_assignments(course_id: Optional[str] = None, module_id: Optional[str] = None, _=Depends(get_current_admin)):
    q: dict = {}
    if course_id:
        q['course_id'] = course_id
    if module_id:
        q['module_id'] = module_id
    assignments = await db.lp_assignments.find(q, {'_id': 0}).to_list(200)
    return assignments


@router.post('/assignments/{assignment_id}/submit')
async def submit_assignment(assignment_id: str, body: AssignmentSubmitIn, _=Depends(get_current_admin)):
    assignment = await db.lp_assignments.find_one({'id': assignment_id}, {'_id': 0})
    if not assignment:
        raise HTTPException(404, 'Assignment not found')
    submission_id = str(uuid.uuid4())
    doc = {
        'id': submission_id,
        'assignment_id': assignment_id,
        'user_id': body.user_id,
        'file_url': body.file_url,
        'notes': body.notes,
        'submitted_at': _now(),
        'status': 'submitted',
    }
    await db.assignment_submissions.insert_one(doc)
    doc.pop('_id', None)
    return doc


@router.post('/assignments/{assignment_id}/grade')
async def grade_assignment(assignment_id: str, body: AssignmentGradeIn, _=Depends(get_current_admin)):
    assignment = await db.lp_assignments.find_one({'id': assignment_id}, {'_id': 0})
    if not assignment:
        raise HTTPException(404, 'Assignment not found')
    submissions = await db.assignment_submissions.find({'assignment_id': assignment_id}, {'_id': 0}).to_list(100)
    if not submissions:
        raise HTTPException(400, 'No submissions found')
    latest = submissions[-1]
    updates = {
        'score': body.score,
        'feedback': body.feedback,
        'graded_by': body.graded_by,
        'graded_at': _now(),
        'status': 'graded',
    }
    await db.assignment_submissions.update_one({'id': latest['id']}, {'$set': updates})
    return {**latest, **updates}


@router.get('/assignments/{assignment_id}/submissions')
async def list_assignment_submissions(assignment_id: str, _=Depends(get_current_admin)):
    assignment = await db.lp_assignments.find_one({'id': assignment_id}, {'_id': 0})
    if not assignment:
        raise HTTPException(404, 'Assignment not found')
    submissions = await db.assignment_submissions.find({'assignment_id': assignment_id}, {'_id': 0}).sort('submitted_at', -1).to_list(200)
    return {'assignment': assignment, 'submissions': submissions}


# ===== Progress & Leaderboard =====

@router.get('/progress/{user_id}')
async def user_progress(user_id: str, _=Depends(get_current_admin)):
    enrollments = await db.enrollments.find({'user_id': user_id}, {'_id': 0}).to_list(200)
    courses_completed = sum(1 for e in enrollments if e.get('progress', 0) >= 1.0)
    total_courses = len(enrollments)
    overall_completion = round(courses_completed / total_courses * 100, 1) if total_courses > 0 else 0

    quiz_submissions = await db.quiz_submissions.find({'user_id': user_id}, {'_id': 0}).to_list(500)
    quizzes_passed = sum(1 for s in quiz_submissions if s.get('passed'))
    avg_quiz_score = round(sum(s.get('score', 0) for s in quiz_submissions) / len(quiz_submissions), 2) if quiz_submissions else 0

    assignment_subs = await db.assignment_submissions.find({'user_id': user_id}, {'_id': 0}).to_list(500)
    assignments_graded = sum(1 for s in assignment_subs if s.get('status') == 'graded')

    certs = await db.certificates.find({'user_id': user_id}, {'_id': 0}).to_list(100)
    certificates_earned = len(certs)

    total_points = sum(s.get('score', 0) for s in quiz_submissions) + sum(s.get('score', 0) for s in assignment_subs if s.get('status') == 'graded')

    total_hours_remaining = 0
    for e in enrollments:
        course = await db.courses.find_one({'slug': e.get('course_slug', '')}, {'_id': 0})
        if course and e.get('progress', 0) < 1.0:
            remaining = (1 - e.get('progress', 0)) * course.get('duration_hours', 10)
            total_hours_remaining += remaining

    return {
        'user_id': user_id,
        'courses_completed': courses_completed,
        'total_courses': total_courses,
        'quizzes_passed': quizzes_passed,
        'avg_quiz_score': avg_quiz_score,
        'assignments_graded': assignments_graded,
        'certificates_earned': certificates_earned,
        'total_points': total_points,
        'overall_completion': overall_completion,
        'estimated_hours_remaining': round(total_hours_remaining, 1),
    }


@router.get('/leaderboard')
async def leaderboard(sort_by: str = 'total_points', limit: int = 20, _=Depends(get_current_admin)):
    users = await db.users.find({}, {'_id': 0, 'password_hash': 0}).to_list(500)
    board = []
    for u in users:
        uid = u['id']
        enrollments = await db.enrollments.find({'user_id': uid}, {'_id': 0}).to_list(200)
        courses_completed = sum(1 for e in enrollments if e.get('progress', 0) >= 1.0)

        quiz_subs = await db.quiz_submissions.find({'user_id': uid}, {'_id': 0}).to_list(500)
        avg_score = round(sum(s.get('score', 0) for s in quiz_subs) / len(quiz_subs), 2) if quiz_subs else 0

        certs = await db.certificates.find({'user_id': uid}, {'_id': 0}).to_list(100)

        assignment_subs = await db.assignment_submissions.find({'user_id': uid}, {'_id': 0}).to_list(500)
        total_points = sum(s.get('score', 0) for s in quiz_subs) + sum(s.get('score', 0) for s in assignment_subs if s.get('status') == 'graded')

        board.append({
            'user_id': uid,
            'name': u.get('name', ''),
            'courses_completed': courses_completed,
            'avg_quiz_score': avg_score,
            'certificates_earned': len(certs),
            'total_points': total_points,
        })

    sort_key = sort_by
    if sort_key not in ('courses_completed', 'avg_quiz_score', 'certificates_earned', 'total_points'):
        sort_key = 'total_points'
    board.sort(key=lambda x: x.get(sort_key, 0), reverse=True)
    return {'leaderboard': board[:limit], 'sort_by': sort_key}


# ===== Learning Paths =====

@router.post('/learning-paths')
async def create_learning_path(body: LearningPathIn, _=Depends(get_current_admin)):
    path_id = str(uuid.uuid4())
    doc = {
        'id': path_id,
        **body.model_dump(),
        'enrolled_users': [],
        'created_at': _now(),
    }
    await db.learning_paths.insert_one(doc)
    doc.pop('_id', None)
    return doc


@router.get('/learning-paths')
async def list_learning_paths(_=Depends(get_current_admin)):
    paths = await db.learning_paths.find({}, {'_id': 0}).to_list(200)
    for p in paths:
        courses = []
        for cid in p.get('courses', []):
            c = await db.courses.find_one({'id': cid}, {'_id': 0})
            courses.append(c)
        p['course_details'] = courses
    return paths


@router.post('/learning-paths/{path_id}/enroll')
async def enroll_in_path(path_id: str, user=Depends(get_current_user)):
    path = await db.learning_paths.find_one({'id': path_id}, {'_id': 0})
    if not path:
        raise HTTPException(404, 'Learning path not found')
    enrolled = path.get('enrolled_users', [])
    if user['id'] in enrolled:
        return {'message': 'Already enrolled'}
    enrolled.append(user['id'])
    await db.learning_paths.update_one({'id': path_id}, {'$set': {'enrolled_users': enrolled}})
    for cid in path.get('courses', []):
        course = await db.courses.find_one({'id': cid}, {'_id': 0})
        if course:
            slug = course.get('slug', '')
            existing = await db.enrollments.find_one({'user_id': user['id'], 'course_slug': slug}, {'_id': 0})
            if not existing:
                enr_doc = {
                    'id': str(uuid.uuid4()),
                    'user_id': user['id'],
                    'course_slug': slug,
                    'progress': 0,
                    'completed_lessons': [],
                    'enrolled_at': _now(),
                }
                await db.enrollments.insert_one(enr_doc)
                await db.courses.update_one({'slug': slug}, {'$inc': {'enrollments_count': 1}})
    return {'enrolled': True}


@router.get('/learning-paths/{path_id}/progress')
async def path_progress(path_id: str, user=Depends(get_current_user)):
    path = await db.learning_paths.find_one({'id': path_id}, {'_id': 0})
    if not path:
        raise HTTPException(404, 'Learning path not found')
    courses = path.get('courses', [])
    total_courses = len(courses)
    completed_courses = 0
    course_progress = []
    for cid in courses:
        course = await db.courses.find_one({'id': cid}, {'_id': 0})
        if not course:
            course_progress.append({'course_id': cid, 'course_title': 'Unknown', 'progress': 0})
            continue
        slug = course.get('slug', '')
        enrollment = await db.enrollments.find_one({'user_id': user['id'], 'course_slug': slug}, {'_id': 0})
        prog = enrollment.get('progress', 0) if enrollment else 0
        if prog >= 1.0:
            completed_courses += 1
        course_progress.append({
            'course_id': cid,
            'course_title': course.get('title', ''),
            'progress': prog,
        })
    overall_progress = round(completed_courses / total_courses * 100, 1) if total_courses > 0 else 0
    return {
        'path_id': path_id,
        'title': path.get('title', ''),
        'total_courses': total_courses,
        'completed_courses': completed_courses,
        'overall_progress': overall_progress,
        'course_progress': course_progress,
    }
