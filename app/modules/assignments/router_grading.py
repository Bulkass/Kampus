import os

from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session
from datetime import datetime
from app.core.database import get_db
from app.core.dependencies import get_current_teacher
from app.models import User
from app.models import Assignment, Submission
from app.models import Grade

router = APIRouter(prefix="/grading", tags=["Grading"])


@router.post("/submission/{submission_id}/grade")
async def grade_submission(
        submission_id: int,
        grade: int = Form(None),
        comment: str = Form(None),
        action: str = Form(...),  # "grade", "reject", "return_for_rework"
        current_user: User = Depends(get_current_teacher),
        db: Session = Depends(get_db)
):
    """
    SF-03.5: Проверка работы и выставление оценки
    """
    submission = db.query(Submission).join(Assignment).join(
        Assignment.lesson
    ).filter(
        Submission.id == submission_id,
        Assignment.lesson.has(teacher_id=current_user.id)
    ).first()

    if not submission:
        raise HTTPException(404, "Решение не найдено или нет доступа")

    if action == "grade":
        if not grade or grade < 2 or grade > 5:
            raise HTTPException(400, "Некорректная оценка (допустимы значения 2-5)")

        submission.status = "graded"
        submission.grade = grade
        submission.comment = comment
        submission.checked_at = datetime.utcnow()

        # SF-02.3: Обновляем оценки в журнале
        # Создаем или обновляем запись в Grade
        existing_grade = db.query(Grade).filter(
            Grade.student_id == submission.student_id,
            Grade.lesson_id == submission.assignment.lesson_id
        ).first()

        if existing_grade:
            existing_grade.grade_value = grade
            existing_grade.comment = comment
        else:
            new_grade = Grade(
                student_id=submission.student_id,
                subject_id=submission.assignment.lesson.subject_id,
                lesson_id=submission.assignment.lesson_id,
                grade_value=grade,
                grade_type="numeric",
                comment=comment
            )
            db.add(new_grade)

    elif action == "reject":
        submission.status = "rejected"
        submission.comment = comment
        submission.checked_at = datetime.utcnow()

    elif action == "return_for_rework":
        submission.status = "returned"
        submission.comment = comment
        submission.checked_at = datetime.utcnow()

    else:
        raise HTTPException(400, "Недопустимое действие")

    db.commit()

    return {
        "message": f"Статус работы обновлен: {submission.status}",
        "submission_id": submission.id,
        "status": submission.status,
        "grade": submission.grade
    }


@router.get("/assignment/{assignment_id}/submissions")
async def get_assignment_submissions(
        assignment_id: int,
        current_user: User = Depends(get_current_teacher),
        db: Session = Depends(get_db)
):
    """
    SF-03.4: Получение всех решений по заданию
    """
    assignment = db.query(Assignment).join(Assignment.lesson).filter(
        Assignment.id == assignment_id,
        Assignment.lesson.has(teacher_id=current_user.id)
    ).first()

    if not assignment:
        raise HTTPException(404, "Задание не найдено")

    submissions = db.query(Submission).filter(
        Submission.assignment_id == assignment_id
    ).all()

    return {
        "assignment_id": assignment_id,
        "assignment_title": assignment.title,
        "total_students": len(assignment.lesson.group.students),
        "submissions": [
            {
                "id": s.id,
                "student_id": s.student_id,
                "student_name": s.student.user.full_name,
                "upload_date": s.upload_date.isoformat(),
                "status": s.status,
                "grade": s.grade,
                "file_path": s.file_path,
                "is_late": s.upload_date > assignment.deadline if assignment.deadline else False
            }
            for s in submissions
        ]
    }


@router.get("/submission/{submission_id}/download")
async def download_submission_file(
        submission_id: int,
        current_user: User = Depends(get_current_teacher),
        db: Session = Depends(get_db)
):
    """
    SF-03.4: Скачивание файла решения
    """
    from fastapi.responses import FileResponse

    submission = db.query(Submission).join(Assignment).join(
        Assignment.lesson
    ).filter(
        Submission.id == submission_id,
        Assignment.lesson.has(teacher_id=current_user.id)
    ).first()

    if not submission or not submission.file_path:
        raise HTTPException(404, "Файл не найден")

    if not os.path.exists(submission.file_path):
        raise HTTPException(404, "Файл отсутствует на сервере")

    return FileResponse(
        submission.file_path,
        filename=f"submission_{submission_id}_{submission.student.user.full_name}.{submission.file_path.split('.')[-1]}"
    )