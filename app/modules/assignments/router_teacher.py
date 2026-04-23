from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional, List
import os
import uuid
from datetime import datetime
from app.core.database import get_db
from app.core.dependencies import get_current_teacher
from app.core.models import User
from app.modules.assignments.models import Assignment
from app.modules.schedule.models import Lesson

router = APIRouter(prefix="/teacher/assignments", tags=["Teacher Assignments"])

UPLOAD_DIR = "media/assignments"
MAX_FILE_SIZE = 15 * 1024 * 1024  # 15 MB
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "pptx"}


# Вспомогательная функция
def validate_file(file: UploadFile) -> tuple[bool, str]:
    """SF-03: Валидация файла"""
    if not file:
        return True, ""

    # Проверка расширения
    ext = file.filename.split(".")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"Недопустимый формат файла. Разрешены: {', '.join(ALLOWED_EXTENSIONS)}"

    # Проверка размера (упрощенно, лучше через чтение чанков)
    file.file.seek(0, 2)  # В конец файла
    size = file.file.tell()
    file.file.seek(0)  # В начало

    if size > MAX_FILE_SIZE:
        return False, f"Файл слишком большой. Максимальный размер: {MAX_FILE_SIZE // (1024 * 1024)} МБ"

    return True, ""


# SF-03: CRUD операций

@router.post("/create")
async def create_assignment(
        lesson_id: int = Form(...),
        title: str = Form(...),
        description: str = Form(None),
        deadline: str = Form(...),
        max_grade: int = Form(5),
        file: Optional[UploadFile] = File(None),
        current_user: User = Depends(get_current_teacher),
        db: Session = Depends(get_db)
):
    """
    SF-03: Создание нового задания
    """
    # Проверяем доступ к уроку
    lesson = db.query(Lesson).filter(
        Lesson.id == lesson_id,
        Lesson.teacher_id == current_user.id
    ).first()

    if not lesson:
        raise HTTPException(403, "Нет доступа к этому уроку")

    # Валидация файла
    file_path = None
    file_size = None
    file_type = None

    if file:
        is_valid, error_msg = validate_file(file)
        if not is_valid:
            raise HTTPException(400, error_msg)

        # Сохраняем файл
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        ext = file.filename.split(".")[-1]
        filename = f"{uuid.uuid4()}.{ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)

        content = await file.read()
        file_size = len(content)
        file_type = ext

        with open(file_path, "wb") as f:
            f.write(content)

    # Создаем задание
    assignment = Assignment(
        lesson_id=lesson_id,
        title=title,
        description=description,
        deadline=datetime.fromisoformat(deadline),
        file_path=file_path,
        file_size=file_size,
        file_type=file_type,
        max_grade=max_grade
    )

    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    return {
        "id": assignment.id,
        "title": assignment.title,
        "deadline": assignment.deadline.isoformat(),
        "message": "Задание успешно создано"
    }


@router.get("/list")
async def list_teacher_assignments(
        lesson_id: Optional[int] = None,
        current_user: User = Depends(get_current_teacher),
        db: Session = Depends(get_db)
):
    """
    SF-03: Список заданий преподавателя
    """
    query = db.query(Assignment).join(Lesson).filter(
        Lesson.teacher_id == current_user.id
    )

    if lesson_id:
        query = query.filter(Assignment.lesson_id == lesson_id)

    assignments = query.order_by(Assignment.created_at.desc()).all()

    return [
        {
            "id": a.id,
            "title": a.title,
            "lesson_id": a.lesson_id,
            "subject_name": a.lesson.subject.name,
            "group_name": a.lesson.group.name,
            "deadline": a.deadline.isoformat() if a.deadline else None,
            "submissions_count": len(a.submissions),
            "created_at": a.created_at.isoformat()
        }
        for a in assignments
    ]


@router.put("/{assignment_id}")
async def update_assignment(
        assignment_id: int,
        title: str = Form(None),
        description: str = Form(None),
        deadline: str = Form(None),
        file: Optional[UploadFile] = File(None),
        current_user: User = Depends(get_current_teacher),
        db: Session = Depends(get_db)
):
    """
    SF-03: Обновление задания
    """
    assignment = db.query(Assignment).join(Lesson).filter(
        Assignment.id == assignment_id,
        Lesson.teacher_id == current_user.id
    ).first()

    if not assignment:
        raise HTTPException(404, "Задание не найдено")

    if title:
        assignment.title = title
    if description:
        assignment.description = description
    if deadline:
        assignment.deadline = datetime.fromisoformat(deadline)

    if file:
        is_valid, error_msg = validate_file(file)
        if not is_valid:
            raise HTTPException(400, error_msg)

        # Удаляем старый файл если есть
        if assignment.file_path and os.path.exists(assignment.file_path):
            os.remove(assignment.file_path)

        # Сохраняем новый
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        ext = file.filename.split(".")[-1]
        filename = f"{uuid.uuid4()}.{ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)

        content = await file.read()
        assignment.file_path = file_path
        assignment.file_size = len(content)
        assignment.file_type = ext

        with open(file_path, "wb") as f:
            f.write(content)

    db.commit()

    return {"message": "Задание обновлено", "id": assignment_id}


@router.delete("/{assignment_id}")
async def delete_assignment(
        assignment_id: int,
        current_user: User = Depends(get_current_teacher),
        db: Session = Depends(get_db)
):
    """
    SF-03: Удаление задания
    """
    assignment = db.query(Assignment).join(Lesson).filter(
        Assignment.id == assignment_id,
        Lesson.teacher_id == current_user.id
    ).first()

    if not assignment:
        raise HTTPException(404, "Задание не найдено")

    # Удаляем файл
    if assignment.file_path and os.path.exists(assignment.file_path):
        os.remove(assignment.file_path)

    # Удаляем файлы решений
    for submission in assignment.submissions:
        if submission.file_path and os.path.exists(submission.file_path):
            os.remove(submission.file_path)

    db.delete(assignment)
    db.commit()

    return {"message": "Задание удалено"}