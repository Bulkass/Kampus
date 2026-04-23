from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.modules.schedule.models import Replacement


def get_week_dates(week_offset: int = 0) -> dict:
    """Возвращает даты для каждого дня недели"""
    today = datetime.now().date()
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)

    return {
        "monday": (monday + timedelta(days=0)).isoformat(),
        "tuesday": (monday + timedelta(days=1)).isoformat(),
        "wednesday": (monday + timedelta(days=2)).isoformat(),
        "thursday": (monday + timedelta(days=3)).isoformat(),
        "friday": (monday + timedelta(days=4)).isoformat(),
        "saturday": (monday + timedelta(days=5)).isoformat()
    }


def apply_replacements(lesson_data: dict, lesson_id: int, target_date: str, db: Session) -> dict:
    """
    SF-01.4: Применяет замены к уроку на конкретную дату
    """
    replacement = db.query(Replacement).filter(
        Replacement.lesson_id == lesson_id,
        Replacement.date == target_date,
        Replacement.status == "active"
    ).first()

    if replacement:
        # Замена найдена - модифицируем данные урока
        if replacement.new_room:
            lesson_data["room"] = replacement.new_room
        if replacement.new_teacher_id:
            lesson_data["teacher_name"] = replacement.new_teacher.user.full_name
        lesson_data["is_replaced"] = True
        lesson_data["replacement_reason"] = replacement.reason
    else:
        lesson_data["is_replaced"] = False

    return lesson_data