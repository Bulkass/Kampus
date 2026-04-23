from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.core.database import engine, Base, init_db
from app.core.config import settings

# Импорт всех моделей
from app.core.models import User, Student, Teacher, Group
from app.modules.schedule.models import Subject, Lesson, Replacement
from app.modules.assignments.models import Assignment, Submission
from app.modules.gradebook.models import Attendance, Grade

# Создание приложения
app = FastAPI(
    title=settings.APP_NAME,
    description="API для системы управления обучением",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение роутеров
from app.modules.auth.router import router as auth_router
app.include_router(auth_router)

from app.modules.schedule.router import router as schedule_router
app.include_router(schedule_router)

from app.modules.gradebook.router import router as gradebook_router
app.include_router(gradebook_router)

from app.modules.assignments.router_teacher import router as teacher_router
app.include_router(teacher_router)

from app.modules.assignments.router_student import router as student_router
app.include_router(student_router)

from app.modules.assignments.router_grading import router as grading_router
app.include_router(grading_router)

# Статические файлы
os.makedirs(settings.ASSIGNMENTS_UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.SUBMISSIONS_UPLOAD_DIR, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.UPLOAD_DIR), name="media")

# События запуска
@app.on_event("startup")
async def startup():
    """Запуск приложения"""
    settings.print_settings()
    print("📦 Создание таблиц...")
    Base.metadata.create_all(bind=engine)
    print("✅ Приложение готово к работе!")

# Корневые эндпоинты
@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "db_type": settings.DB_TYPE,
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "database": settings.DB_TYPE,
        "debug": settings.DEBUG,
    }

# Запуск
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
