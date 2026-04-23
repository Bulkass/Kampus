from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import os
from dotenv import load_dotenv
import urllib

# Загружаем переменные окружения
load_dotenv()

# ============================================
# КОНФИГУРАЦИЯ БАЗЫ ДАННЫХ
# ============================================

# Вариант 1: SQLite (для разработки)
SQLITE_DATABASE_URL = "sqlite:///./school.db"


# Вариант 2: SQL Server (для продакшена)
def get_sql_server_url() -> str:
    """
    Формирует URL подключения к SQL Server

    Использует Windows Authentication или SQL Server Authentication
    """
    driver = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")
    server = os.getenv("DB_SERVER", "localhost\\SQLEXPRESS")
    database = os.getenv("DB_NAME", "LMS_Database")

    # SQL Server Authentication
    username = os.getenv("DB_USERNAME")
    password = os.getenv("DB_PASSWORD")

    if username and password:
        # С аутентификацией SQL Server
        params = urllib.parse.quote_plus(
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password};"
            f"TrustServerCertificate=yes;"  # Для SSMS 2022
            f"Encrypt=yes;"
        )
    else:
        # Windows Authentication (Trusted Connection)
        params = urllib.parse.quote_plus(
            f"DRIVER={{{driver}}};"
            f"SERVER={server};"
            f"DATABASE={database};"
            f"Trusted_Connection=yes;"
            f"TrustServerCertificate=yes;"
            f"Encrypt=yes;"
        )

    return f"mssql+pyodbc:///?odbc_connect={params}"


# Выбираем URL в зависимости от окружения
USE_SQL_SERVER = os.getenv("USE_SQL_SERVER", "false").lower() == "true"

if USE_SQL_SERVER:
    DATABASE_URL = get_sql_server_url()
else:
    DATABASE_URL = os.getenv("DATABASE_URL", SQLITE_DATABASE_URL)

print(f"🔗 Подключение к БД: {DATABASE_URL[:50]}...")

# Создаем движок базы данных
if DATABASE_URL.startswith("mssql"):
    # SQL Server
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        echo=False,  # Поставь True для отладки SQL запросов
    )
elif DATABASE_URL.startswith("sqlite"):
    # SQLite
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL или другие
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
    print("📦 Создание таблиц...")
    Base.metadata.create_all(bind=engine)
    print("✅ Таблицы успешно созданы")


def test_connection():
    """
    Проверка подключения к БД
    """
    try:
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            print("✅ Подключение к базе данных успешно!")
            return True
    except Exception as e:
        print(f"❌ Ошибка подключения к БД: {e}")
        return False


def get_engine():
    """Получение движка БД"""
    return engine