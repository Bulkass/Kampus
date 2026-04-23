from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Dict, Any
from app.core.database import get_db
from app.core.dependencies import get_current_student
from app.core.models import User, Student
from app.modules.schedule.models import Lesson, Group
from app.modules.schedule.service import get_week_dates, apply_replacements

router = APIRouter(prefix="/schedule", tags=["Schedule"])


@router.get("/student/week")
async def get_student_weekly_schedule(
        week_offset: int = Query(0, description="0=текущая неделя, 1=следующая, -1=прошлая"),
        current_user: User = Depends(get_current_student),
        db: Session = Depends(get_db)
):
    """
    SF-01.1: Получение расписания студента на неделю
    """
    # Получаем профиль студента с группой
    student = db.query(Student).filter(Student.id == current_user.id).first()
    if not student or not student.group_id:
        return {"error": "Студент не привязан к группе"}

    # Определяем даты недели
    week_dates = get_week_dates(week_offset)

    # Получаем базовое расписание
    lessons = db.query(Lesson).filter(
        Lesson.group_id == student.group_id
    ).all()

    # Формируем расписание по дням
    schedule = {
        "monday": [],
        "tuesday": [],
        "wednesday": [],
        "thursday": [],
        "friday": [],
        "saturday": [],
        "week_dates": week_dates,
        "group_name": student.group.name
    }

    days_map = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]

    for lesson in lessons:
        day_name = days_map[lesson.day_of_week]

        lesson_data = {
            "id": lesson.id,
            "subject_name": lesson.subject.name,
            "subject_code": lesson.subject.code,
            "teacher_name": lesson.teacher.user.full_name,
            "start_time": lesson.start_time.strftime("%H:%M"),
            "end_time": lesson.end_time.strftime("%H:%M"),
            "room": lesson.room,
            "has_assignment": len(lesson.assignments) > 0
        }

        schedule[day_name].append(lesson_data)

    # Сортируем по времени
    for day in days_map:
        schedule[day].sort(key=lambda x: x["start_time"])

    return schedule


@router.get("/student/week/with-replacements")
async def get_student_schedule_with_replacements(
        week_offset: int = Query(0),
        current_user: User = Depends(get_current_student),
        db: Session = Depends(get_db)
):
    """
    SF-01.1 + SF-01.4: Расписание с учетом замен
    """
    student = db.query(Student).filter(Student.id == current_user.id).first()
    if not student:
        return {"error": "Студент не найден"}

    week_dates = get_week_dates(week_offset)
    days_map = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]

    lessons = db.query(Lesson).filter(
        Lesson.group_id == student.group_id
    ).all()

    schedule = {day: [] for day in days_map}
    schedule["week_dates"] = week_dates

    for lesson in lessons:
        day_name = days_map[lesson.day_of_week]
        target_date = week_dates[day_name]

        lesson_data = {
            "id": lesson.id,
            "subject_name": lesson.subject.name,
            "teacher_name": lesson.teacher.user.full_name,
            "start_time": lesson.start_time.strftime("%H:%M"),
            "end_time": lesson.end_time.strftime("%H:%M"),
            "room": lesson.room,
            "assignments": [
                {
                    "id": a.id,
                    "title": a.title,
                    "deadline": a.deadline.isoformat() if a.deadline else None
                } for a in lesson.assignments
            ]
        }

        # SF-01.4: Применяем замены
        lesson_data = apply_replacements(lesson_data, lesson.id, target_date, db)

        schedule[day_name].append(lesson_data)

    return schedule


@router.get("/teacher/week")
async def get_teacher_weekly_schedule(
        week_offset: int = Query(0),
        current_user: User = Depends(get_current_teacher),
        db: Session = Depends(get_db)
):
    """
    SF-01.1 (преподаватель): Получение расписания преподавателя на неделю
    """
    teacher = db.query(Teacher).filter(Teacher.id == current_user.id).first()
    if not teacher:
        return {"error": "Преподаватель не найден"}

    week_dates = get_week_dates(week_offset)
    days_map = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]

    # Получаем все уроки преподавателя
    lessons = db.query(Lesson).filter(
        Lesson.teacher_id == teacher.id
    ).all()

    schedule = {day: [] for day in days_map}
    schedule["week_dates"] = week_dates
    schedule["teacher_name"] = current_user.full_name

    for lesson in lessons:
        day_name = days_map[lesson.day_of_week]
        target_date = week_dates[day_name]

        lesson_data = {
            "id": lesson.id,
            "subject_name": lesson.subject.name,
            "group_name": lesson.group.name,
            "group_id": lesson.group.id,
            "start_time": lesson.start_time.strftime("%H:%M"),
            "end_time": lesson.end_time.strftime("%H:%M"),
            "room": lesson.room,
            "students_count": len(lesson.group.students),
            "has_assignments": len(lesson.assignments) > 0
        }

        # SF-01.4: Применяем замены
        lesson_data = apply_replacements(lesson_data, lesson.id, target_date, db)

        schedule[day_name].append(lesson_data)

    # Сортируем по времени
    for day in days_map:
        schedule[day].sort(key=lambda x: x["start_time"])

    return schedule