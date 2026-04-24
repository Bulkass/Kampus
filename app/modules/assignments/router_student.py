import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

# Импорты из ядра
from app.core.database import get_db
from app.models import User, Student
from app.core.dependencies import get_current_student

# Импорты моделей из других модулей
from app.models import Assignment, Submission
from app.models import Lesson

router = APIRouter(prefix="/student/assignments", tags=["Student Assignments"])

# Конфигурация загрузки файлов
SUBMISSION_UPLOAD_DIR = "media/submissions"
MAX_FILE_SIZE = 15 * 1024 * 1024  # 15 MB
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "pptx", "xlsx", "zip"}


# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================

def validate_file(file: UploadFile):
    """
    Проверка файла на размер и расширение
    """
    # Проверка расширения
    if file.filename:
        ext = file.filename.split(".")[-1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Недопустимый формат файла. Разрешены: {', '.join(ALLOWED_EXTENSIONS)}"
            )

    # Проверка размера файла
    file.file.seek(0, 2)  # В конец файла
    size = file.file.tell()
    file.file.seek(0)  # Возврат в начало

    if size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Файл слишком большой. Максимальный размер: {MAX_FILE_SIZE // (1024 * 1024)} МБ"
        )

    return ext


def save_upload_file(file: UploadFile, student_id: int, assignment_id: int) -> str:
    """
    Сохраняет файл на диск и возвращает путь к нему
    """
    os.makedirs(SUBMISSION_UPLOAD_DIR, exist_ok=True)

    ext = file.filename.split(".")[-1]
    filename = f"{student_id}_{assignment_id}_{uuid.uuid4()}.{ext}"
    file_path = os.path.join(SUBMISSION_UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        content = file.file.read()
        buffer.write(content)

    return file_path


# ============================================
# SF-03.1: СПИСОК ЗАДАНИЙ СТУДЕНТА
# ============================================

@router.get("/my")
async def get_student_assignments(
        status_filter: str = None,  # "active", "submitted", "graded", "overdue"
        current_user: User = Depends(get_current_student),
        db: Session = Depends(get_db)
):
    """
    SF-03.1: Получение списка заданий для текущего студента
    """
    # Получаем профиль студента
    student = current_user.student_profile
    if not student or not student.group_id:
        raise HTTPException(
            status_code=404,
            detail="Профиль студента не найден или не привязан к группе"
        )

    # Получаем все задания для группы
    assignments = db.query(Assignment).join(Lesson).filter(
        Lesson.group_id == student.group_id
    ).all()

    result = []
    now = datetime.utcnow()

    for assignment in assignments:
        # Ищем Submission студента по этому заданию
        submission = db.query(Submission).filter(
            Submission.assignment_id == assignment.id,
            Submission.student_id == student.id
        ).first()

        # Определяем статус
        if submission:
            submission_status = submission.status
            grade = submission.grade
            submission_id = submission.id
            upload_date = submission.upload_date.isoformat()
        else:
            submission_status = "not_submitted"
            grade = None
            submission_id = None
            upload_date = None

        # Проверяем, не просрочен ли дедлайн
        is_overdue = False
        if assignment.deadline and assignment.deadline < now and submission_status == "not_submitted":
            is_overdue = True

        assignment_data = {
            "id": assignment.id,
            "title": assignment.title,
            "description": assignment.description,
            "subject_name": assignment.lesson.subject.name if assignment.lesson.subject else "N/A",
            "teacher_name": assignment.lesson.teacher.user.full_name if assignment.lesson.teacher else "N/A",
            "deadline": assignment.deadline.isoformat() if assignment.deadline else None,
            "is_overdue": is_overdue,
            "max_grade": assignment.max_grade,
            "file_available": assignment.file_path is not None,
            "submission_status": submission_status,
            "submission_id": submission_id,
            "grade": grade,
            "upload_date": upload_date
        }

        # Фильтрация по статусу (если указан)
        if status_filter:
            if status_filter == "active" and submission_status != "not_submitted":
                continue
            elif status_filter == "submitted" and submission_status not in ["submitted", "checking"]:
                continue
            elif status_filter == "graded" and submission_status != "graded":
                continue
            elif status_filter == "overdue" and not is_overdue:
                continue

        result.append(assignment_data)

    # Сортировка: сначала с ближайшим дедлайном, потом без дедлайна
    result.sort(key=lambda x: x["deadline"] if x["deadline"] else "9999-12-31")

    return {
        "student_name": current_user.full_name,
        "group_name": student.group.name if student.group else "N/A",
        "total_assignments": len(result),
        "assignments": result
    }


# ============================================
# SF-03.3: ОТПРАВКА РЕШЕНИЯ (Submission)
# ============================================

@router.post("/{assignment_id}/submit")
async def submit_assignment(
        assignment_id: int,
        file: UploadFile = File(...),
        current_user: User = Depends(get_current_student),
        db: Session = Depends(get_db)
):
    """
    SF-03.3: Отправка решения задания студентом

    - **assignment_id**: ID задания
    - **file**: Файл с решением
    """
    # Проверяем студента
    student = current_user.student_profile
    if not student:
        raise HTTPException(
            status_code=404,
            detail="Профиль студента не найден"
        )

    # Проверяем существование задания
    assignment = db.query(Assignment).filter(
        Assignment.id == assignment_id
    ).first()

    if not assignment:
        raise HTTPException(
            status_code=404,
            detail="Задание не найдено"
        )

    # Проверяем, что задание для группы этого студента
    if assignment.lesson.group_id != student.group_id:
        raise HTTPException(
            status_code=403,
            detail="Это задание не для вашей группы"
        )

    # Валидация файла
    validate_file(file)

    # SF-03.2: Проверка дедлайна
    now = datetime.utcnow()
    is_late = False
    if assignment.deadline and assignment.deadline < now:
        is_late = True
        # Можно разрешить отправку с пометкой "late" или запретить
        # Здесь разрешаем с предупреждением

    # Проверяем, есть ли уже отправленное решение
    existing_submission = db.query(Submission).filter(
        Submission.assignment_id == assignment_id,
        Submission.student_id == student.id
    ).first()

    if existing_submission:
        # Удаляем старый файл если есть
        if existing_submission.file_path and os.path.exists(existing_submission.file_path):
            os.remove(existing_submission.file_path)

        # Сохраняем новый файл
        file_path = save_upload_file(file, student.id, assignment_id)
        file_size = os.path.getsize(file_path)

        # Обновляем запись
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
            "is_late": is_late,
            "upload_date": now.isoformat()
        }
    else:
        # Создаем новую отправку
        file_path = save_upload_file(file, student.id, assignment_id)
        file_size = os.path.getsize(file_path)

        submission = Submission(
            assignment_id=assignment_id,
            student_id=student.id,
            file_path=file_path,
            file_size=file_size,
            upload_date=now,
            status="submitted" if not is_late else "submitted_late"
        )

        db.add(submission)
        db.commit()
        db.refresh(submission)

        return {
            "message": "Решение отправлено",
            "submission_id": submission.id,
            "is_late": is_late,
            "upload_date": now.isoformat()
        }


# ============================================
# SF-03.2: ПРОВЕРКА СТАТУСА ОТПРАВКИ
# ============================================

@router.get("/{assignment_id}/my-submission")
async def get_my_submission(
        assignment_id: int,
        current_user: User = Depends(get_current_student),
        db: Session = Depends(get_db)
):
    """
    Получение информации о своей отправке по заданию
    """
    student = current_user.student_profile
    if not student:
        raise HTTPException(404, detail="Профиль студента не найден")

    submission = db.query(Submission).filter(
        Submission.assignment_id == assignment_id,
        Submission.student_id == student.id
    ).first()

    if not submission:
        return {
            "status": "not_submitted",
            "assignment_id": assignment_id
        }

    return {
        "id": submission.id,
        "assignment_id": submission.assignment_id,
        "upload_date": submission.upload_date.isoformat(),
        "status": submission.status,
        "grade": submission.grade,
        "comment": submission.comment,
        "file_name": os.path.basename(submission.file_path) if submission.file_path else None
    }


# ============================================
# СКАЧИВАНИЕ ФАЙЛА ЗАДАНИЯ
# ============================================

@router.get("/{assignment_id}/download")
async def download_assignment_file(
        assignment_id: int,
        current_user: User = Depends(get_current_student),
        db: Session = Depends(get_db)
):
    """
    Скачивание файла задания
    """
    from fastapi.responses import FileResponse

    student = current_user.student_profile
    if not student:
        raise HTTPException(404, detail="Студент не найден")

    assignment = db.query(Assignment).filter(
        Assignment.id == assignment_id
    ).first()

    if not assignment:
        raise HTTPException(404, detail="Задание не найдено")

    if not assignment.file_path:
        raise HTTPException(404, detail="У задания нет прикрепленного файла")

    if not os.path.exists(assignment.file_path):
        raise HTTPException(404, detail="Файл задания отсутствует на сервере")

    return FileResponse(
        path=assignment.file_path,
        filename=os.path.basename(assignment.file_path),
        media_type="application/octet-stream"
    )


# ============================================
# УДАЛЕНИЕ СВОЕЙ ОТПРАВКИ (опционально)
# ============================================

@router.delete("/submission/{submission_id}")
async def delete_my_submission(
        submission_id: int,
        current_user: User = Depends(get_current_student),
        db: Session = Depends(get_db)
):
    """
    Удаление своей отправки (если она еще не проверена)
    """
    student = current_user.student_profile
    if not student:
        raise HTTPException(404, detail="Студент не найден")

    submission = db.query(Submission).filter(
        Submission.id == submission_id,
        Submission.student_id == student.id
    ).first()

    if not submission:
        raise HTTPException(404, detail="Отправка не найдена")

    if submission.status in ["graded", "checking"]:
        raise HTTPException(
            status_code=403,
            detail="Нельзя удалить проверенную или проверяемую работу"
        )

    # Удаляем файл
    if submission.file_path and os.path.exists(submission.file_path):
        os.remove(submission.file_path)

    db.delete(submission)
    db.commit()

    return {"message": "Отправка удалена"}