from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

# Импорт из database.py
from app.core.database import engine, Base, init_db

# Импорт ВСЕХ моделей (чтобы создать таблицы)
from app.core.models import User, Student, Teacher, Group
from app.modules.schedule.models import Subject, Lesson, Replacement
from app.modules.assignments.models import Assignment, Submission
from app.modules.gradebook.models import Attendance, Grade

# ============================================
# СОЗДАНИЕ ПРИЛОЖЕНИЯ
# ============================================

app = FastAPI(
    title="LMS Core API",
    description="Ядро системы управления обучением",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ============================================
# CORS НАСТРОЙКИ
# ============================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# ПОДКЛЮЧЕНИЕ РОУТЕРОВ
# ============================================

from app.modules.auth.router import router as auth_router
app.include_router(auth_router)

from app.modules.schedule.router import router as schedule_router
app.include_router(schedule_router)

from app.modules.gradebook.router import router as gradebook_router
app.include_router(gradebook_router)

from app.modules.assignments.router_teacher import router as teacher_assignments_router
app.include_router(teacher_assignments_router)

from app.modules.assignments.router_student import router as student_assignments_router
app.include_router(student_assignments_router)

from app.modules.assignments.router_grading import router as grading_router
app.include_router(grading_router)

# ============================================
# СТАТИЧЕСКИЕ ФАЙЛЫ
# ============================================

os.makedirs("media", exist_ok=True)
os.makedirs("media/assignments", exist_ok=True)
os.makedirs("media/submissions", exist_ok=True)

app.mount("/media", StaticFiles(directory="media"), name="media")

# ============================================
# СОБЫТИЯ ЗАПУСКА
# ============================================

@app.on_event("startup")
async def startup_event():
    """Создание таблиц при запуске"""
    print("🚀 Запуск приложения...")
    Base.metadata.create_all(bind=engine)
    print("✅ Таблицы созданы")

# ============================================
# КОРНЕВЫЕ ЭНДПОИНТЫ
# ============================================

@app.get("/")
async def root():
    return {
        "app": "LMS Core API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "database": "connected"}

# ============================================
# ЗАПУСК
# ============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )