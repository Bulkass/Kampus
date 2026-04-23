from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db
from app.core.models import User, UserRole
from app.core.security import decode_token

# OAuth2 схема
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/auth/login/form",
    auto_error=True
)

# Blacklist для токенов (импортируем из auth модуля)
try:
    from app.modules.auth.router import token_blacklist
except ImportError:
    token_blacklist = set()


async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db)
) -> User:
    """
    Получение текущего пользователя из JWT токена
    """
    # Проверка blacklist
    if token in token_blacklist:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен отозван. Выполните вход заново.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Декодирование токена
    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен аутентификации",
            headers={"WWW-Authenticate": "Bearer"},
        )

    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Некорректный токен: отсутствует идентификатор пользователя"
        )

    # Поиск пользователя в БД
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден в системе"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт деактивирован. Обратитесь к администратору."
        )

    return user


async def get_current_active_user(
        current_user: User = Depends(get_current_user)
) -> User:
    """Проверка что пользователь активен"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт не активен"
        )
    return current_user


async def get_current_admin(
        current_user: User = Depends(get_current_user)
) -> User:
    """Проверка прав администратора"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуются права администратора"
        )
    return current_user


async def get_current_teacher(
        current_user: User = Depends(get_current_user)
) -> User:
    """Проверка прав преподавателя"""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуются права преподавателя"
        )

    # Проверяем что у преподавателя есть профиль
    if not current_user.teacher_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль преподавателя не найден. Обратитесь к администратору."
        )

    return current_user


async def get_current_student(
        current_user: User = Depends(get_current_user)
) -> User:
    """Проверка прав студента"""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Требуются права студента"
        )

    # Проверяем что у студента есть профиль
    if not current_user.student_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Профиль студента не найден. Обратитесь к администратору."
        )

    return current_user