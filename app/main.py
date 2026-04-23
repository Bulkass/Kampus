from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import engine, Base

# Импорт всех моделей для создания таблиц
from app.core.models import User, Student, Teacher, Group
from app.modules.schedule.models import Subject, Lesson, Replacement
from app.modules.assignments.models import Assignment, Submission
from app.modules.gradebook.models import Attendance, Grade

# Импорт роутеров
from app.modules.auth.router import router as auth_router
from app.modules.schedule.router import router as schedule_router
from app.modules.gradebook.router import router as gradebook_router
from app.modules.assignments.router_teacher import router as teacher_assignments_router
from app.modules.assignments.router_student import router as student_assignments_router
from app.modules.assignments.router_grading import router as grading_router

# Создание таблиц
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="LMS Core API",
    description="Ядро системы управления обучением",
    version="1.0.0"
)

# CORS для фронтенда
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Адреса фронтенда
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
app.include_router(auth_router)
app.include_router(schedule_router)
app.include_router(gradebook_router)
app.include_router(teacher_assignments_router)
app.include_router(student_assignments_router)
app.include_router(grading_router)

@app.get("/")
async def root():
    return {
        "message": "LMS Core API запущен",
        "docs": "/docs",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}