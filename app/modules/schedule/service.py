from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import Dict, Any


def get_week_dates(week_offset: int = 0) -> Dict[str, str]:
    """
    Возвращает даты для каждого дня недели

    Args:
        week_offset: 0 = текущая неделя, 1 = следующая, -1 = прошлая

    Returns:
        Dict с датами для каждого дня
    """
    today = datetime.now().date()

    # Находим понедельник текущей недели
    monday = today - timedelta(days=today.weekday())

    # Применяем смещение
    target_monday = monday + timedelta(weeks=week_offset)

    return {
        "monday": (target_monday + timedelta(days=0)).isoformat(),
        "tuesday": (target_monday + timedelta(days=1)).isoformat(),
        "wednesday": (target_monday + timedelta(days=2)).isoformat(),
        "thursday": (target_monday + timedelta(days=3)).isoformat(),
        "friday": (target_monday + timedelta(days=4)).isoformat(),
        "saturday": (target_monday + timedelta(days=5)).isoformat(),
        "sunday": (target_monday + timedelta(days=6)).isoformat(),
    }


def apply_replacements(lesson_data: Dict[str, Any], lesson_id: int, target_date: str, db: Session) -> Dict[str, Any]:
    """
    SF-01.4: Применяет замены к уроку на конкретную дату

    Args:
        lesson_data: Данные урока
        lesson_id: ID урока
        target_date: Дата в формате YYYY-MM-DD
        db: Сессия БД

    Returns:
        Обновленные данные урока с учетом замен
    """
    from app.modules.schedule.models import Replacement

    # Ищем замену на эту дату
    replacement = db.query(Replacement).filter(
        Replacement.lesson_id == lesson_id,
        Replacement.date == target_date,
        Replacement.status == "active"
    ).first()

    if replacement:
        # Замена найдена - модифицируем данные урока
        lesson_data["is_replaced"] = True
        lesson_data["replacement_reason"] = replacement.reason or "Замена"
        lesson_data["original_room"] = lesson_data.get("room")

        if replacement.new_room:
            lesson_data["room"] = replacement.new_room

        if replacement.new_teacher_id and replacement.new_teacher:
            lesson_data["teacher_name"] = replacement.new_teacher.user.full_name
            lesson_data["original_teacher"] = lesson_data.get("teacher_name")

    else:
        lesson_data["is_replaced"] = False

    return lesson_data