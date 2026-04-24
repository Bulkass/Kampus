# app/core/security.py
import hashlib
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from app.core.config import settings

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверка пароля через SHA-256
    """
    salt = hashed_password[:32]  # Первые 32 символа — соль
    stored_hash = hashed_password[32:]  # Остальное — хеш

    new_hash = hashlib.sha256((salt + plain_password).encode()).hexdigest()
    return new_hash == stored_hash


def get_password_hash(password: str) -> str:
    """
    Создание хеша пароля
    """
    salt = os.urandom(16).hex()  # Генерируем соль
    pwd_hash = hashlib.sha256((salt + password).encode()).hexdigest()
    return salt + pwd_hash  # Соль + хеш


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Создание JWT токена
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Декодирование JWT токена
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None