import re
import uuid
from fastapi import APIRouter, HTTPException, Depends
from db import db
from models import (
    Course, CourseIn, Module, ModuleIn, Lesson, LessonIn,
    Enrollment, TutorChatIn,
)
from auth import get_current_user, get_current_admin
from llm_provider import chat_completion
from subscription import can_access_advanced, effective_subscription

router = APIRouter(tags=['learning'])


def _slug(name: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')


# ===== Public catalog =====
@router.get('/courses')
async def list_courses(level: str | None = None, featured: bool | None = None):
    q = {'is_published': True}
    if level:
        q['level'] = level
    if featured is not None:
        q['is_featured'] = featured
    return await db.courses.find(q, {'_id': 0}).to_list(100)


@router.get('/courses/{slug}')
async def get_course(slug: str):
    course = await db.courses.find_one({'slug': slug, 'is_published': True}, {'_id': 0})
    if not course:
        raise HTTPException(404, 'Course not found')
    modules = await db.modules.find({'course_slug': slug}, {'_id': 0}).sort('order', 1).to_list(50)
    lessons = await db.lessons.find({'course_slug': slug}, {'_id': 0}).sort('order', 1).to_list(200)
    # nest lessons in modules
    mods_with_lessons = []
    for m in modules:
        m['lessons'] = [l for l in lessons if l.get('module_id') == m['id']]
        mods_with_lessons.append(m)
    course['modules'] = mods_with_lessons
    course['total_lessons'] = len(lessons)
    return course


# ===== Enrollment =====
@router.post('/courses/{slug}/enroll')
async def enroll(slug: str, user=Depends(get_current_user)):
    course = await db.courses.find_one({'slug': slug}, {'_id': 0})
    if not course:
        raise HTTPException(404, 'Course not found')
    # Gate Advanced (premium) courses
    if course.get('level') == 'Advanced' or course.get('is_premium'):
        allowed = await can_access_advanced(user)
        if not allowed:
            raise HTTPException(402, 'This is a Pro course. Upgrade to enroll.')
    existing = await db.enrollments.find_one({'user_id': user['id'], 'course_slug': slug}, {'_id': 0})
    if existing:
        return existing
    enr = Enrollment(user_id=user['id'], course_slug=slug)
    await db.enrollments.insert_one(enr.model_dump())
    await db.courses.update_one({'slug': slug}, {'$inc': {'enrollments_count': 1}})
    return enr.model_dump()


@router.get('/me/enrollments')
async def my_enrollments(user=Depends(get_current_user)):
    enrs = await db.enrollments.find({'user_id': user['id']}, {'_id': 0}).to_list(100)
    # enrich with course details
    for e in enrs:
        c = await db.courses.find_one({'slug': e['course_slug']}, {'_id': 0})
        e['course'] = c
    return enrs


@router.get('/courses/{slug}/learn')
async def learn(slug: str, user=Depends(get_current_user)):
    enr = await db.enrollments.find_one({'user_id': user['id'], 'course_slug': slug}, {'_id': 0})
    if not enr:
        raise HTTPException(403, 'Not enrolled')
    course = await get_course(slug)
    return {'course': course, 'enrollment': enr}


@router.post('/lessons/{lesson_id}/complete')
async def complete_lesson(lesson_id: str, user=Depends(get_current_user)):
    lesson = await db.lessons.find_one({'id': lesson_id}, {'_id': 0})
    if not lesson:
        raise HTTPException(404, 'Lesson not found')
    enr = await db.enrollments.find_one({'user_id': user['id'], 'course_slug': lesson['course_slug']}, {'_id': 0})
    if not enr:
        raise HTTPException(403, 'Not enrolled')
    completed = set(enr.get('completed_lessons', []))
    completed.add(lesson_id)
    total = await db.lessons.count_documents({'course_slug': lesson['course_slug']})
    progress = len(completed) / total if total else 0
    updates = {'completed_lessons': list(completed), 'progress': progress}
    if progress >= 1.0 and not enr.get('completed_at'):
        from datetime import datetime, timezone
        updates['completed_at'] = datetime.now(timezone.utc).isoformat()
    await db.enrollments.update_one({'id': enr['id']}, {'$set': updates})
    return {'progress': progress, 'completed_lessons': list(completed)}


# ===== AI Tutor =====
@router.post('/courses/{slug}/tutor')
async def tutor(slug: str, body: TutorChatIn, user=Depends(get_current_user)):
    course = await db.courses.find_one({'slug': slug}, {'_id': 0})
    if not course:
        raise HTTPException(404, 'Course not found')
    lesson_ctx = ''
    if body.lesson_id:
        lesson = await db.lessons.find_one({'id': body.lesson_id}, {'_id': 0})
        if lesson:
            lesson_ctx = f"\nCurrent lesson: {lesson['title']}\nLesson summary: {lesson.get('description', '')}"
    system = f"""You are an encouraging, patient AI Tutor for getszy.com's AI Learning Academy.
You help women learn AI from basic to advanced, in a friendly Hinglish + English tone.
Keep answers concise, motivating, and practical. Use simple analogies. Suggest next steps.

Course: {course['title']} ({course['level']})
Description: {course.get('description', '')}
Learning outcomes: {', '.join(course.get('outcomes', []))}{lesson_ctx}

Student name: {user['name']}.
NEVER include code unless the question is about code. NEVER refuse polite learning questions."""
    session_id = body.session_id or f"tutor-{user['id']}-{slug}"
    reply = await chat_completion(system=system, user=body.message, session_id=session_id, temperature=0.6)
    # log
    await db.tutor_messages.insert_one({
        'id': str(uuid.uuid4()), 'session_id': session_id, 'user_id': user['id'],
        'course_slug': slug, 'lesson_id': body.lesson_id,
        'user_msg': body.message, 'reply': reply,
        'created_at': __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),
    })
    return {'reply': reply, 'session_id': session_id}


@router.get('/me/courses/{slug}/certificate')
async def certificate(slug: str, user=Depends(get_current_user)):
    enr = await db.enrollments.find_one({'user_id': user['id'], 'course_slug': slug}, {'_id': 0})
    if not enr or enr.get('progress', 0) < 1.0:
        raise HTTPException(400, 'Course not yet completed')
    course = await db.courses.find_one({'slug': slug}, {'_id': 0})
    return {
        'student_name': user['name'],
        'course_title': course['title'],
        'course_level': course['level'],
        'completed_at': enr.get('completed_at'),
        'instructor': course.get('instructor', 'Getszy AI Team'),
        'certificate_id': enr['id'][:8].upper(),
    }


# ===== Admin =====
@router.get('/admin/courses', dependencies=[Depends(get_current_admin)])
async def admin_list_courses():
    return await db.courses.find({}, {'_id': 0}).to_list(500)


@router.post('/admin/courses', dependencies=[Depends(get_current_admin)])
async def admin_create_course(body: CourseIn):
    slug = _slug(body.title)
    if await db.courses.find_one({'slug': slug}):
        raise HTTPException(400, 'Course slug exists')
    c = Course(slug=slug, **body.model_dump())
    await db.courses.insert_one(c.model_dump())
    return c.model_dump()


@router.put('/admin/courses/{slug}', dependencies=[Depends(get_current_admin)])
async def admin_update_course(slug: str, body: dict):
    body.pop('id', None); body.pop('slug', None)
    await db.courses.update_one({'slug': slug}, {'$set': body})
    return await db.courses.find_one({'slug': slug}, {'_id': 0})


@router.delete('/admin/courses/{slug}', dependencies=[Depends(get_current_admin)])
async def admin_delete_course(slug: str):
    await db.courses.delete_one({'slug': slug})
    await db.modules.delete_many({'course_slug': slug})
    await db.lessons.delete_many({'course_slug': slug})
    return {'deleted': True}


@router.post('/admin/modules', dependencies=[Depends(get_current_admin)])
async def admin_create_module(body: ModuleIn):
    m = Module(**body.model_dump())
    await db.modules.insert_one(m.model_dump())
    return m.model_dump()


@router.delete('/admin/modules/{module_id}', dependencies=[Depends(get_current_admin)])
async def admin_delete_module(module_id: str):
    await db.modules.delete_one({'id': module_id})
    await db.lessons.delete_many({'module_id': module_id})
    return {'deleted': True}


@router.post('/admin/lessons', dependencies=[Depends(get_current_admin)])
async def admin_create_lesson(body: LessonIn):
    l = Lesson(**body.model_dump())
    await db.lessons.insert_one(l.model_dump())
    return l.model_dump()


@router.put('/admin/lessons/{lesson_id}', dependencies=[Depends(get_current_admin)])
async def admin_update_lesson(lesson_id: str, body: dict):
    body.pop('id', None)
    await db.lessons.update_one({'id': lesson_id}, {'$set': body})
    return await db.lessons.find_one({'id': lesson_id}, {'_id': 0})


@router.delete('/admin/lessons/{lesson_id}', dependencies=[Depends(get_current_admin)])
async def admin_delete_lesson(lesson_id: str):
    await db.lessons.delete_one({'id': lesson_id})
    return {'deleted': True}


@router.get('/admin/enrollments', dependencies=[Depends(get_current_admin)])
async def admin_enrollments(course_slug: str | None = None):
    q = {}
    if course_slug:
        q['course_slug'] = course_slug
    enrs = await db.enrollments.find(q, {'_id': 0}).sort('enrolled_at', -1).to_list(500)
    for e in enrs:
        u = await db.users.find_one({'id': e['user_id']}, {'_id': 0, 'password_hash': 0})
        e['user'] = u
    return enrs
