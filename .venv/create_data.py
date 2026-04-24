# create_data.py
from app.core.database import SessionLocal
from app.models import User, Teacher, Group, Subject, Lesson
from datetime import time

db = SessionLocal()

# 1. Проверяем пользователя-учителя (уже есть)
teacher_user = db.query(User).filter(User.email == "teacher@test.com").first()
if teacher_user:
    print("✅ Пользователь teacher@test.com уже есть! ID:", teacher_user.id)
else:
    # На всякий случай создаём, но такого не должно быть
    from app.core.security import get_password_hash

    teacher_user = User(
        email="teacher@test.com",
        password_hash=get_password_hash("123456"),
        full_name="Петрова Анна",
        role="teacher",
        is_active=True
    )
    db.add(teacher_user)
    db.commit()
    print("✅ Создан пользователь teacher@test.com! ID:", teacher_user.id)

# 2. Проверяем профиль учителя
teacher = db.query(Teacher).filter(Teacher.id == teacher_user.id).first()
if teacher:
    print("✅ Профиль учителя уже есть! ID:", teacher.id)
else:
    teacher = Teacher(id=teacher_user.id, department="ИТ", employee_id="T001")
    db.add(teacher)
    db.commit()
    print("✅ Профиль учителя создан! ID:", teacher.id)

# 3. Создаём уроки
group = db.query(Group).first()
subjects = db.query(Subject).all()

if group and teacher and len(subjects) >= 2:
    lessons = [
        (0, subjects[0].id, "09:00", "10:30", "310"),
        (0, subjects[1].id, "11:00", "12:30", "315"),
        (1, subjects[0].id, "09:00", "10:30", "310"),
    ]

    for day, subj_id, start, end, room in lessons:
        lesson = Lesson(
            group_id=group.id,
            subject_id=subj_id,
            teacher_id=teacher.id,
            day_of_week=day,
            start_time=time.fromisoformat(start),
            end_time=time.fromisoformat(end),
            room=room
        )
        db.add(lesson)

    db.commit()
    print("✅ Уроки созданы!")

    for l in db.query(Lesson).all():
        print(f"  ID: {l.id} | День: {l.day_of_week} | Комната: {l.room}")
else:
    print("❌ Не хватает данных")

db.close()
print("Готово!")