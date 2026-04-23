import os
from typing import List, Set

# Пытаемся загрузить .env файл
try:
    from dotenv import load_dotenv

    load_dotenv()
    print("✅ .env файл загружен")
except ImportError:
    print("⚠️ python-dotenv не установлен. Используем значения по умолчанию.")
except Exception as e:
    print(f"⚠️ Не удалось загрузить .env: {e}. Используем значения по умолчанию.")


class Settings:
    """
    Централизованные настройки приложения

    Все настройки имеют значения по умолчанию,
    которые можно переопределить через .env файл
    """

    # ============================================
    # БАЗА ДАННЫХ
    # ============================================

    @property
    def USE_SQL_SERVER(self) -> bool:
        """Использовать ли SQL Server"""
        return os.getenv("USE_SQL_SERVER", "false").lower() == "true"

    @property
    def DATABASE_URL(self) -> str:
        """
        URL подключения к базе данных

        Для SQLite:
            DATABASE_URL=sqlite:///./school.db

        Для PostgreSQL:
            DATABASE_URL=postgresql://user:pass@localhost:5432/dbname

        Для MySQL:
            DATABASE_URL=mysql+pymysql://user:pass@localhost:3306/dbname
        """
        return os.getenv("DATABASE_URL", "sqlite:///./school.db")

    @property
    def DB_SERVER(self) -> str:
        """Адрес SQL Server (только для MSSQL)"""
        return os.getenv("DB_SERVER", "localhost\\SQLEXPRESS")

    @property
    def DB_NAME(self) -> str:
        """Имя базы данных (только для MSSQL)"""
        return os.getenv("DB_NAME", "LMS_Database")

    @property
    def DB_USERNAME(self) -> str:
        """Имя пользователя БД (только для MSSQL)"""
        return os.getenv("DB_USERNAME", "")

    @property
    def DB_PASSWORD(self) -> str:
        """Пароль пользователя БД (только для MSSQL)"""
        return os.getenv("DB_PASSWORD", "")

    @property
    def DB_DRIVER(self) -> str:
        """ODBC драйвер для SQL Server"""
        return os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")

    # ============================================
    # БЕЗОПАСНОСТЬ
    # ============================================

    @property
    def SECRET_KEY(self) -> str:
        """Секретный ключ для JWT токенов"""
        return os.getenv("SECRET_KEY", "default-secret-key-change-me-in-production")

    @property
    def ALGORITHM(self) -> str:
        """Алгоритм шифрования JWT"""
        return os.getenv("ALGORITHM", "HS256")

    @property
    def ACCESS_TOKEN_EXPIRE_MINUTES(self) -> int:
        """Время жизни токена доступа (в минутах)"""
        return int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 часа

    # ============================================
    # ПРИЛОЖЕНИЕ
    # ============================================

    @property
    def APP_NAME(self) -> str:
        """Название приложения"""
        return os.getenv("APP_NAME", "LMS Kampus Web Core")

    @property
    def APP_VERSION(self) -> str:
        """Версия приложения"""
        return os.getenv("APP_VERSION", "1.0.0")

    @property
    def DEBUG(self) -> bool:
        """Режим отладки"""
        return os.getenv("DEBUG", "true").lower() == "true"

    @property
    def HOST(self) -> str:
        """Хост для запуска сервера"""
        return os.getenv("HOST", "0.0.0.0")

    @property
    def PORT(self) -> int:
        """Порт для запуска сервера"""
        return int(os.getenv("PORT", "8000"))

    @property
    def API_PREFIX(self) -> str:
        """Префикс для API эндпоинтов"""
        return os.getenv("API_PREFIX", "")

    # ============================================
    # ЗАГРУЗКА ФАЙЛОВ
    # ============================================

    @property
    def MAX_UPLOAD_SIZE(self) -> int:
        """Максимальный размер загружаемого файла (в байтах)"""
        return int(os.getenv("MAX_UPLOAD_SIZE", "15728640"))  # 15 MB

    @property
    def ALLOWED_EXTENSIONS(self) -> Set[str]:
        """Разрешённые расширения файлов"""
        extensions = os.getenv(
            "ALLOWED_EXTENSIONS",
            "pdf,docx,txt,pptx,xlsx,zip,jpg,jpeg,png"
        )
        return set(ext.strip() for ext in extensions.split(","))

    @property
    def UPLOAD_DIR(self) -> str:
        """Папка для загрузки файлов"""
        return os.getenv("UPLOAD_DIR", "media")

    @property
    def ASSIGNMENTS_UPLOAD_DIR(self) -> str:
        """Папка для файлов заданий"""
        return os.path.join(self.UPLOAD_DIR, "assignments")

    @property
    def SUBMISSIONS_UPLOAD_DIR(self) -> str:
        """Папка для файлов решений студентов"""
        return os.path.join(self.UPLOAD_DIR, "submissions")

    # ============================================
    # CORS (ДОСТУП С ФРОНТЕНДА)
    # ============================================

    @property
    def ALLOWED_ORIGINS(self) -> List[str]:
        """
        Разрешённые источники для CORS

        Можно переопределить в .env:
            ALLOWED_ORIGINS=http://localhost:3000,http://myapp.com
        """
        origins = os.getenv(
            "ALLOWED_ORIGINS",
            "http://localhost:3000,http://localhost:5173,http://localhost:8080"
        )
        return [origin.strip() for origin in origins.split(",")]

    # ============================================
    # НАСТРОЙКИ БД (ДЛЯ УДОБСТВА)
    # ============================================

    @property
    def DB_TYPE(self) -> str:
        """
        Определяет тип базы данных

        Returns:
            "sqlite", "mssql", "postgresql", "mysql"
        """
        if self.USE_SQL_SERVER:
            return "mssql"

        url = self.DATABASE_URL.lower()

        if url.startswith("sqlite"):
            return "sqlite"
        elif url.startswith("postgresql"):
            return "postgresql"
        elif url.startswith("mysql"):
            return "mysql"
        else:
            return "unknown"

    # ============================================
    # ВЫВОД ТЕКУЩИХ НАСТРОЕК (ДЛЯ ОТЛАДКИ)
    # ============================================

    def print_settings(self):
        """Выводит текущие настройки в консоль (без паролей)"""
        print("=" * 50)
        print("📋 ТЕКУЩИЕ НАСТРОЙКИ ПРИЛОЖЕНИЯ")
        print("=" * 50)
        print(f"🔄 USE_SQL_SERVER: {self.USE_SQL_SERVER}")
        print(f"🗄️  DB_TYPE: {self.DB_TYPE}")
        print(f"🔗 DATABASE_URL: {self._mask_url(self.DATABASE_URL)}")
        print(f"📦 DB_SERVER: {self.DB_SERVER}")
        print(f"📦 DB_NAME: {self.DB_NAME}")
        print(f"📱 APP_NAME: {self.APP_NAME}")
        print(f"📱 VERSION: {self.APP_VERSION}")
        print(f"🐛 DEBUG: {self.DEBUG}")
        print(f"🌐 HOST: {self.HOST}")
        print(f"🔌 PORT: {self.PORT}")
        print(f"📁 UPLOAD_DIR: {self.UPLOAD_DIR}")
        print(f"📏 MAX_UPLOAD_SIZE: {self.MAX_UPLOAD_SIZE // (1024 * 1024)} MB")
        print(f"🔑 TOKEN_EXPIRE: {self.ACCESS_TOKEN_EXPIRE_MINUTES} минут")
        print(f"🌍 ALLOWED_ORIGINS: {self.ALLOWED_ORIGINS}")
        print("=" * 50)

    @staticmethod
    def _mask_url(url: str) -> str:
        """Скрывает пароль в URL для безопасного вывода"""
        if "://" in url and "@" in url:
            parts = url.split("@")
            before_at = parts[0].split("://")
            if ":" in before_at[-1]:
                before_at[-1] = before_at[-1].split(":")[0] + ":****"
            return "://".join(before_at) + "@" + parts[-1]
        return url


# ============================================
# СОЗДАЁМ ГЛОБАЛЬНЫЙ ЭКЗЕМПЛЯР НАСТРОЕК
# ============================================

settings = Settings()

# ============================================
# ТЕСТОВЫЙ ВЫВОД ПРИ ИМПОРТЕ
# ============================================

if __name__ == "__main__":
    # Если запустить этот файл напрямую - покажет настройки
    settings.print_settings()