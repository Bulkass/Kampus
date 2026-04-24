from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.core.database import engine, Base

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

# Статика
os.makedirs("static", exist_ok=True)
os.makedirs("media", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)
    print("🚀 Сервер запущен: http://localhost:8000")
    print("📚 API Docs: http://localhost:8000/docs")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)