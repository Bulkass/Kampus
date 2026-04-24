from typing import Dict, List, Any
from sqlalchemy.orm import Session
from statistics import mean


def calculate_student_averages(gradebook: Dict, db: Session) -> Dict:
    """
    SF-02.3: Расчёт среднего балла по студенту и предметам
    """
    for student in gradebook["students"]:
        subject_grades = {}
        all_grades = []

        # Группируем оценки по предметам
        for lesson_key, grades_list in student["grades"].items():
            # Извлекаем subject_id из lesson
            for grade in grades_list:
                if grade["type"] == "numeric" and grade["value"] > 0:
                    # Здесь нужна логика определения subject_id
                    # Упрощенно: все числовые оценки идут в общий список
                    all_grades.append(grade["value"])

        # Средний балл студента
        student["average_score"] = round(mean(all_grades), 2) if all_grades else 0

        # Средний балл по предметам (заглушка)
        student["subject_averages"] = {}

    return gradebook


def calculate_subject_average_for_group(group_id: int, subject_id: int, db: Session) -> float:
    """
    SF-02.3: Средний балл группы по предмету
    """
    from app.models import Grade, Attendance

    grades = db.query(Grade).filter(
        Grade.subject_id == subject_id,
        Grade.student.has(group_id=group_id),
        Grade.grade_type == "numeric",
        Grade.grade_value > 0
    ).all()

    if not grades:
        return 0.0

    return round(mean([g.grade_value for g in grades]), 2)


def calculate_attendance_stats(student_id: int, start_date: str, end_date: str, db: Session) -> Dict:
    """
    SF-02.4: Расчёт статистики пропусков за период
    """
    from app.models import Attendance

    from datetime import datetime

    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)

    attendances = db.query(Attendance).filter(
        Attendance.student_id == student_id,
        Attendance.date >= start,
        Attendance.date <= end
    ).all()

    total_lessons = len(attendances)
    attended = sum(1 for a in attendances if a.is_present)
    absent = total_lessons - attended
    late = sum(1 for a in attendances if a.late_minutes > 0)

    attendance_rate = (attended / total_lessons * 100) if total_lessons > 0 else 0

    return {
        "total_lessons": total_lessons,
        "attended": attended,
        "absent": absent,
        "late": late,
        "attendance_rate": round(attendance_rate, 1),
        "period": {
            "start": start_date,
            "end": end_date
        }
    }