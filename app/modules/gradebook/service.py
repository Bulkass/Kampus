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
    from app.modules.gradebook.models import Grade

    grades = db.query(Grade).filter(
        Grade.subject_id == subject_id,
        Grade.student.has(group_id=group_id),
        Grade.grade_type == "numeric",
        Grade.grade_value > 0
    ).all()

    if not grades:
        return 0.0

    return round(mean([g.grade_value for g in grades]), 2)