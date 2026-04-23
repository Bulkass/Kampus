from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.core.database import get_db
from app.core.dependencies import get_current_student
from app.core.models import User, Student
from app.modules.assignments.models import Assignment, Submission
from app.modules.schedule.models import Lesson

router = APIRouter(prefix="/student/assignments", tags=["Student Assignments"])


@router.get("/my")
async def get_student_assignments(
        status: str = None,  # "active", "submitted", "graded"
        current_user: User = Depends(get_current_student),
        db: Session = Depends(get_db)
):
    """
    SF-03.1: Список заданий для студента
    """
    student = db.query(Student).filter(Student.id == current_user.id).first()
    if not student:
        raise HTTPException(404, "Студент не найден")

    # Получаем все задания для группы студента
    assignments = db.query(Assignment).join(Lesson).filter(
        Lesson.group_id == student.group_id
    ).all()

    result = []
    now = datetime.utcnow()

    for assignment in assignments:
        # Проверяем статус сдачи
        submission = db.query(Submission).filter(
            Submission.assignment_id == assignment.id,
            Submission.student_id == student.id
        ).first()

        assignment_data = {
            "id": assignment.id,
            "title": assignment.title,
            "description": assignment.description,
            "subject_name": assignment.lesson.subject.name,
            "teacher_name": assignment.lesson.teacher.user.full_name,
            "deadline": assignment.deadline.isoformat() if assignment.deadline else None,
            "is_overdue": assignment.deadline < now if assignment.deadline else False,
            "file_available": assignment.file_path is not None,
            "max_grade": assignment.max_grade,
            "submission_status": "not_submitted"
        }

        if submission:
            assignment_data["submission_status"] = submission.status
            assignment_data["submission_id"] = submission.id
            assignment_data["grade"] = submission.grade
            assignment_data["upload_date"] = submission.upload_date.isoformat()
            if submission.status == "graded":
                assignment_data["comment"] = submission.comment

        # Фильтр по статусу
        if status:
            if status == "active" and submission:
                continue
            elif status == "submitted" and (not submission or submission.status != "submitted"):
                continue
            elif status == "graded" and (not submission or submission.status != "graded"):
                continue

        result.append(assignment_data)

    # Сортируем по дедлайну (ближайшие сверху)
    result.sort(key=lambda x: x["deadline"] if x["deadline"] else "9999")

    return result