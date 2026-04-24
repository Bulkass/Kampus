# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.core.database import engine, Base
from app.core.config import settings

# Импорт ВСЕХ моделей из одного файла
from app.models import (
    User, Group, Student, Teacher,
    Subject, Lesson, Replacement,
    Assignment, Submission,
    Attendance, Grade, Recommendation
)

app = FastAPI(title="LMS Kampus", version="1.0.0", docs_url="/docs")

# CORS
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# API роутеры
from app.modules.auth.router import router as auth_router
app.include_router(auth_router)

# ============================================
# СТАТИЧЕСКИЕ ФАЙЛЫ — ВАЖНО! Должно быть ДО главной страницы
# ============================================
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ============================================
# ГЛАВНАЯ СТРАНИЦА
# ============================================
@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.get("/login")
async def login_page():
    return FileResponse("static/index.html")

@app.get("/student-schedule")
async def student_page():
    return FileResponse("static/index.html")

@app.get("/teacher-schedule")
async def teacher_page():
    return FileResponse("static/index.html")

@app.get("/assignments")
async def assignments_page():
    return FileResponse("static/index.html")

@app.get("/gradebook")
async def gradebook_page():
    return FileResponse("static/index.html")

# ============================================
# ЗАПУСК
# ============================================
@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)
    print("🚀 Сервер: http://localhost:8000")
    print("📄 Вход: http://localhost:8000/login")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)