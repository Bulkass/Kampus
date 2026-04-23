# app/core/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# ============================================
# НАСТРОЙКА БАЗЫ ДАННЫХ
# ============================================

# Для SQLite (по умолчанию)
SQLITE_DATABASE_URL = "sqlite:///./school.db"

# URL базы данных из переменных окружения или SQLite по умолчанию
DATABASE_URL = os.getenv("DATABASE_URL", SQLITE_DATABASE_URL)

# Создаем движок базы данных
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}  # Только для SQLite
    )
else:
    # Для PostgreSQL или других БД
    engine = create_engine(
        DATABASE_URL,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )

# Создаем фабрику сессий
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Базовый класс для всех моделей
Base = declarative_base()


# ============================================
# ФУНКЦИИ ДЛЯ РАБОТЫ С БД
# ============================================

def get_db() -> Generator[Session, None, None]:
    """
    Зависимость FastAPI для получения сессии БД

    Использование в эндпоинтах:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Инициализация базы данных - создание всех таблиц
    """
    Base.metadata.create_all(bind=engine)
    print("✅ База данных инициализирована")


def get_engine():
    """
    Получение движка БД (для миграций Alembic и т.д.)
    """
    return engine