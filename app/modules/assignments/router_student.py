import os
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.core.database import get_db
from app.core.dependencies import get_current_student
from app.core.models import User, Student
from app.modules.assignments.models import Assignment, Submission
from app.modules.assignments.router_teacher import validate_file
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


SUBMISSION_UPLOAD_DIR = "media/submissions"


@router.post("/{assignment_id}/submit")
async def submit_assignment(
        assignment_id: int,
        file: UploadFile = File(...),
        current_user: User = Depends(get_current_student),
        db: Session = Depends(get_db)
):
    """
    SF-03.3: Отправка решения задания
    """
    student = db.query(Student).filter(Student.id == current_user.id).first()
    if not student:
        raise HTTPException(404, "Студент не найден")

    # Проверяем задание
    assignment = db.query(Assignment).filter(
        Assignment.id == assignment_id
    ).first()

    if not assignment:
        raise HTTPException(404, "Задание не найдено")

    # SF-03.2: Проверка дедлайна
    now = datetime.utcnow()
    is_late = False
    if assignment.deadline and assignment.deadline < now:
        is_late = True
        # Можно разрешить отправку с пометкой "опоздание"

    # Проверяем существующую отправку
    existing_submission = db.query(Submission).filter(
        Submission.assignment_id == assignment_id,
        Submission.student_id == student.id
    ).first()

    # Валидация файла
    is_valid, error_msg = validate_file(file)
    if not is_valid:
        raise HTTPException(400, error_msg)

    # Сохраняем файл
    os.makedirs(SUBMISSION_UPLOAD_DIR, exist_ok=True)
    ext = file.filename.split(".")[-1]
    filename = f"{student.id}_{assignment_id}_{uuid.uuid4()}.{ext}"
    file_path = os.path.join(SUBMISSION_UPLOAD_DIR, filename)

    content = await file.read()
    file_size = len(content)

    with open(file_path, "wb") as f:
        f.write(content)

    if existing_submission:
        # Удаляем старый файл
        if existing_submission.file_path and os.path.exists(existing_submission.file_path):
            os.remove(existing_submission.file_path)

        # Обновляем отправку
        existing_submission.file_path = file_path
        existing_submission.file_size = file_size
        existing_submission.upload_date = now
        existing_submission.status = "submitted"
        existing_submission.grade = None
        existing_submission.comment = None

        db.commit()

        return {
            "message": "Решение обновлено",
            "submission_id": existing_submission.id,
            "is_late": is_late
        }
    else:
        # Создаем новую отправку
        submission = Submission(
            assignment_id=assignment_id,
            student_id=student.id,
            file_path=file_path,
            file_size=file_size,
            upload_date=now,
            status="submitted"
        )

        db.add(submission)
        db.commit()
        db.refresh(submission)

        return {
            "message": "Решение отправлено",
            "submission_id": submission.id,
            "is_late": is_late
        }
