from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

# Правильные импорты из core
from app.core.database import get_db
from app.core.models import User, Student, Teacher, Group
from app.core.dependencies import get_current_user, get_current_student, get_current_teacher

# Импорты из этого же модуля
from app.modules.schedule.models import Lesson, Subject, Replacement
from app.modules.schedule.service import get_week_dates, apply_replacements

router = APIRouter(prefix="/schedule", tags=["Schedule"])


# ============================================
# SF-01.1: Расписание студента
# ============================================

@router.get("/student/week")
async def get_student_weekly_schedule(
        week_offset: int = Query(0, description="0=текущая неделя, 1=следующая, -1=прошлая"),
        current_user: User = Depends(get_current_student),
        db: Session = Depends(get_db)
):
    """
    SF-01.1: Получение расписания студента на неделю
    """
    # Проверяем что у пользователя есть профиль студента
    if not current_user.student_profile:
        raise HTTPException(
            status_code=404,
            detail="Профиль студента не найден"
        )

    student = current_user.student_profile

    if not student.group_id:
        raise HTTPException(
            status_code=404,
            detail="Студент не привязан к группе"
        )

    # Получаем даты недели
    week_dates = get_week_dates(week_offset)

    # Получаем базовое расписание
    lessons = db.query(Lesson).filter(
        Lesson.group_id == student.group_id
    ).all()

    # Формируем расписание по дням
    days_map = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    schedule = {day: [] for day in days_map[:6]}  # Только 6 дней
    schedule["week_dates"] = week_dates
    schedule["group_name"] = student.group.name if student.group else "Неизвестная группа"

    for lesson in lessons:
        if lesson.day_of_week >= len(days_map[:6]):
            continue

        day_name = days_map[lesson.day_of_week]

        lesson_data = {
            "id": lesson.id,
            "subject_name": lesson.subject.name if lesson.subject else "Без предмета",
            "subject_code": lesson.subject.code if lesson.subject else "",
            "teacher_name": lesson.teacher.user.full_name if lesson.teacher else "Без преподавателя",
            "start_time": lesson.start_time.strftime("%H:%M") if lesson.start_time else "",
            "end_time": lesson.end_time.strftime("%H:%M") if lesson.end_time else "",
            "room": lesson.room or "",
            "has_assignment": len(lesson.assignments) > 0 if lesson.assignments else False
        }

        schedule[day_name].append(lesson_data)

    # Сортируем по времени
    for day in days_map[:6]:
        schedule[day].sort(key=lambda x: x["start_time"])

    return schedule


# ============================================
# SF-01.1 + SF-01.4: Расписание с заменами
# ============================================

@router.get("/student/week/with-replacements")
async def get_student_schedule_with_replacements(
        week_offset: int = Query(0, description="0=текущая неделя, 1=следующая, -1=прошлая"),
        current_user: User = Depends(get_current_student),
        db: Session = Depends(get_db)
):
    """
    SF-01.1 + SF-01.4: Расписание с учетом замен
    """
    if not current_user.student_profile:
        raise HTTPException(
            status_code=404,
            detail="Профиль студента не найден"
        )

    student = current_user.student_profile

    if not student.group_id:
        raise HTTPException(
            status_code=404,
            detail="Студент не привязан к группе"
        )

    week_dates = get_week_dates(week_offset)
    days_map = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]

    lessons = db.query(Lesson).filter(
        Lesson.group_id == student.group_id
    ).all()

    schedule = {day: [] for day in days_map}
    schedule["week_dates"] = week_dates
    schedule["group_name"] = student.group.name if student.group else ""

    for lesson in lessons:
        if lesson.day_of_week >= 6:
            continue

        day_name = days_map[lesson.day_of_week]
        target_date = week_dates.get(day_name)

        lesson_data = {
            "id": lesson.id,
            "subject_name": lesson.subject.name if lesson.subject else "",
            "teacher_name": lesson.teacher.user.full_name if lesson.teacher else "",
            "start_time": lesson.start_time.strftime("%H:%M") if lesson.start_time else "",
            "end_time": lesson.end_time.strftime("%H:%M") if lesson.end_time else "",
            "room": lesson.room or "",
            "assignments": [
                {
                    "id": a.id,
                    "title": a.title,
                    "deadline": a.deadline.isoformat() if a.deadline else None
                } for a in (lesson.assignments or [])
            ]
        }

        # SF-01.4: Применяем замены если есть дата
        if target_date:
            lesson_data = apply_replacements(lesson_data, lesson.id, target_date, db)

        schedule[day_name].append(lesson_data)

    for day in days_map:
        schedule[day].sort(key=lambda x: x["start_time"])

    return schedule


# ============================================
# SF-01.1: Расписание преподавателя
# ============================================

@router.get("/teacher/week")
async def get_teacher_weekly_schedule(
        week_offset: int = Query(0, description="0=текущая неделя, 1=следующая, -1=прошлая"),
        current_user: User = Depends(get_current_teacher),
        db: Session = Depends(get_db)
):
    """
    SF-01.1 (преподаватель): Получение расписания преподавателя на неделю
    """
    if not current_user.teacher_profile:
        raise HTTPException(
            status_code=404,
            detail="Профиль преподавателя не найден"
        )

    teacher = current_user.teacher_profile

    week_dates = get_week_dates(week_offset)
    days_map = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]

    lessons = db.query(Lesson).filter(
        Lesson.teacher_id == teacher.id
    ).all()

    schedule = {day: [] for day in days_map}
    schedule["week_dates"] = week_dates
    schedule["teacher_name"] = current_user.full_name

    for lesson in lessons:
        if lesson.day_of_week >= 6:
            continue

        day_name = days_map[lesson.day_of_week]
        target_date = week_dates.get(day_name)

        lesson_data = {
            "id": lesson.id,
            "subject_name": lesson.subject.name if lesson.subject else "",
            "group_name": lesson.group.name if lesson.group else "",
            "group_id": lesson.group.id if lesson.group else None,
            "start_time": lesson.start_time.strftime("%H:%M") if lesson.start_time else "",
            "end_time": lesson.end_time.strftime("%H:%M") if lesson.end_time else "",
            "room": lesson.room or "",
            "students_count": len(lesson.group.students) if lesson.group else 0,
            "has_assignments": len(lesson.assignments) > 0 if lesson.assignments else False
        }

        # Применяем замены
        if target_date:
            lesson_data = apply_replacements(lesson_data, lesson.id, target_date, db)

        schedule[day_name].append(lesson_data)

    for day in days_map:
        schedule[day].sort(key=lambda x: x["start_time"])

    return schedule


# ============================================
# SF-01.3: Детали урока для преподавателя
# ============================================

@router.get("/teacher/lesson/{lesson_id}/details")
async def get_lesson_details_for_teacher(
        lesson_id: int,
        target_date: str = Query(..., description="Дата в формате YYYY-MM-DD"),
        current_user: User = Depends(get_current_teacher),
        db: Session = Depends(get_db)
):
    """
    SF-01.3: Детальная информация о паре для преподавателя
    """
    # Проверяем профиль преподавателя
    if not current_user.teacher_profile:
        raise HTTPException(
            status_code=404,
            detail="Профиль преподавателя не найден"
        )

    # Получаем урок с проверкой принадлежности преподавателю
    lesson = db.query(Lesson).filter(
        Lesson.id == lesson_id,
        Lesson.teacher_id == current_user.teacher_profile.id
    ).first()

    if not lesson:
        raise HTTPException(
            status_code=404,
            detail="Урок не найден или нет доступа"
        )

    # Проверяем формат даты
    try:
        datetime.fromisoformat(target_date)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Неверный формат даты. Используйте YYYY-MM-DD"
        )

    # Формируем ответ
    lesson_data = {
        "id": lesson.id,
        "subject": {
            "id": lesson.subject.id,
            "name": lesson.subject.name,
            "code": lesson.subject.code
        } if lesson.subject else None,
        "group": {
            "id": lesson.group.id,
            "name": lesson.group.name,
            "students": [
                {
                    "id": s.id,
                    "full_name": s.user.full_name,
                    "student_id_number": s.student_id_number
                } for s in (lesson.group.students if lesson.group else [])
            ]
        } if lesson.group else None,
        "room": lesson.room,
        "start_time": lesson.start_time.strftime("%H:%M") if lesson.start_time else "",
        "end_time": lesson.end_time.strftime("%H:%M") if lesson.end_time else "",
        "day_of_week": lesson.day_of_week,
        "week_type": lesson.week_type,
        "assignments": [
            {
                "id": a.id,
                "title": a.title,
                "description": a.description,
                "deadline": a.deadline.isoformat() if a.deadline else None,
                "file_path": a.file_path,
                "max_grade": a.max_grade,
                "submissions_count": len(a.submissions) if a.submissions else 0,
                "created_at": a.created_at.isoformat() if a.created_at else None
            } for a in (lesson.assignments or [])
        ]
    }

    # Применяем замены
    lesson_data = apply_replacements(lesson_data, lesson.id, target_date, db)

    return lesson_data


# ============================================
# Общее расписание группы (для админа)
# ============================================

@router.get("/group/{group_id}")
async def get_group_schedule(
        group_id: int,
        week_offset: int = Query(0),
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    Получение расписания группы (доступно админам и преподавателям)
    """
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(
            status_code=404,
            detail="Группа не найдена"
        )

    week_dates = get_week_dates(week_offset)
    days_map = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]

    lessons = db.query(Lesson).filter(
        Lesson.group_id == group_id
    ).all()

    schedule = {day: [] for day in days_map}
    schedule["week_dates"] = week_dates
    schedule["group_name"] = group.name

    for lesson in lessons:
        if lesson.day_of_week >= 6:
            continue

        day_name = days_map[lesson.day_of_week]
        target_date = week_dates.get(day_name)

        lesson_data = {
            "id": lesson.id,
            "subject_name": lesson.subject.name if lesson.subject else "",
            "teacher_name": lesson.teacher.user.full_name if lesson.teacher else "",
            "start_time": lesson.start_time.strftime("%H:%M") if lesson.start_time else "",
            "end_time": lesson.end_time.strftime("%H:%M") if lesson.end_time else "",
            "room": lesson.room or ""
        }

        if target_date:
            lesson_data = apply_replacements(lesson_data, lesson.id, target_date, db)

        schedule[day_name].append(lesson_data)

    for day in days_map:
        schedule[day].sort(key=lambda x: x["start_time"])

    return schedule