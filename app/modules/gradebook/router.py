from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.core.database import get_db
from app.core.dependencies import get_current_teacher
from app.core.models import User, Group, Student
from app.modules.gradebook.models import Grade, Attendance
from app.modules.gradebook.service import calculate_student_averages, calculate_attendance_stats

router = APIRouter(prefix="/gradebook", tags=["Gradebook"])


@router.get("/group/{group_id}")
async def get_group_gradebook(
        group_id: int,
        month: int = Query(None, description="Фильтр по месяцу (1-12)"),
        semester: int = Query(None, description="Фильтр по семестру (1 или 2)"),
        current_user: User = Depends(get_current_teacher),
        db: Session = Depends(get_db)
):
    """
    SF-02.1: Получение журнала оценок для группы
    """
    # Проверяем существование группы
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(404, "Группа не найдена")

    # SF-02.5: Получаем список студентов группы
    students = db.query(Student).filter(
        Student.group_id == group_id
    ).order_by(Student.user.has(full_name=None)).all()

    # Получаем все предметы группы (через уроки)
    from app.modules.schedule.models import Lesson, Subject
    subjects = db.query(Subject).join(Lesson).filter(
        Lesson.group_id == group_id
    ).distinct().all()

    # Формируем структуру журнала
    gradebook = {
        "group_id": group_id,
        "group_name": group.name,
        "subjects": [],
        "students": []
    }

    # Для каждого предмета собираем даты занятий
    for subject in subjects:
        subject_data = {
            "id": subject.id,
            "name": subject.name,
            "lessons": []
        }

        # Получаем уроки по предмету для этой группы
        lessons = db.query(Lesson).filter(
            Lesson.group_id == group_id,
            Lesson.subject_id == subject.id
        ).order_by(Lesson.start_time).all()

        for lesson in lessons:
            # Применяем фильтры по месяцу/семестру
            if month and lesson.start_time.month != month:
                continue
            # Логика фильтра по семестру

            subject_data["lessons"].append({
                "id": lesson.id,
                "date": lesson.start_time.date().isoformat(),
                "topic": f"Занятие {lesson.id}"  # Здесь можно добавить тему
            })

        gradebook["subjects"].append(subject_data)

    # SF-02.5: Формируем строки студентов
    for student in students:
        student_row = {
            "id": student.id,
            "full_name": student.user.full_name,
            "grades": {},
            "attendance": {},
            "average_score": 0
        }

        # Получаем оценки студента
        grades = db.query(Grade).filter(
            Grade.student_id == student.id
        ).all()

        for grade in grades:
            lesson_key = f"lesson_{grade.lesson_id}" if grade.lesson_id else f"subject_{grade.subject_id}"
            if lesson_key not in student_row["grades"]:
                student_row["grades"][lesson_key] = []
            student_row["grades"][lesson_key].append({
                "value": grade.grade_value,
                "type": grade.grade_type,
                "date": grade.date.isoformat()
            })

        # Получаем посещаемость
        attendances = db.query(Attendance).filter(
            Attendance.student_id == student.id
        ).all()

        for att in attendances:
            lesson_key = f"lesson_{att.lesson_id}"
            student_row["attendance"][lesson_key] = {
                "is_present": att.is_present,
                "late_minutes": att.late_minutes,
                "date": att.date.isoformat()
            }

        gradebook["students"].append(student_row)

    # SF-02.3: Расчёт среднего балла
    gradebook = calculate_student_averages(gradebook, db)

    return gradebook


@router.get("/attendance/stats/{student_id}")
async def get_student_attendance_stats(
        student_id: int,
        start_date: str = Query(...),
        end_date: str = Query(...),
        current_user: User = Depends(get_current_teacher),
        db: Session = Depends(get_db)
):
    """
    SF-02.4: Статистика пропусков студента за период
    """
    stats = calculate_attendance_stats(student_id, start_date, end_date, db)
    return stats


@router.get("/attendance/group/{group_id}/stats")
async def get_group_attendance_stats(
        group_id: int,
        month: int = Query(None),
        current_user: User = Depends(get_current_teacher),
        db: Session = Depends(get_db)
):
    """
    SF-02.4: Статистика пропусков по всей группе
    """
    from datetime import datetime, timedelta

    # Определяем период по месяцу
    if month:
        year = datetime.now().year
        start_date = datetime(year, month, 1).date().isoformat()
        if month == 12:
            end_date = datetime(year, 12, 31).date().isoformat()
        else:
            end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
            end_date = end_date.isoformat()
    else:
        # Текущий месяц
        now = datetime.now()
        start_date = datetime(now.year, now.month, 1).date().isoformat()
        end_date = now.date().isoformat()

    # Получаем статистику по каждому студенту
    students = db.query(Student).filter(Student.group_id == group_id).all()

    group_stats = {
        "group_id": group_id,
        "period": {"start": start_date, "end": end_date},
        "students": []
    }

    total_attendance_rate = 0

    for student in students:
        stats = calculate_attendance_stats(student.id, start_date, end_date, db)
        group_stats["students"].append({
            "student_id": student.id,
            "full_name": student.user.full_name,
            "attendance_rate": stats["attendance_rate"],
            "absent": stats["absent"],
            "late": stats["late"]
        })
        total_attendance_rate += stats["attendance_rate"]

    # Средняя посещаемость по группе
    group_stats["average_attendance_rate"] = round(
        total_attendance_rate / len(students), 1
    ) if students else 0

    return group_stats