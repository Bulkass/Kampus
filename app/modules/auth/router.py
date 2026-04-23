from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from app.core.database import get_db
from app.core.models import User
from app.core.security import (
    verify_password,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from pydantic import BaseModel

router = APIRouter(prefix="/auth", tags=["Authentication"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    full_name: str
    user_id: int


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    SF-05.1: Аутентификация пользователя по email и паролю
    Возвращает JWT токен и базовую информацию о пользователе
    """
    # Поиск пользователя
    user = db.query(User).filter(User.email == request.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Проверка пароля
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Проверка активности аккаунта
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт деактивирован"
        )

    # Создание токена
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role.value},
        expires_delta=access_token_expires
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        role=user.role.value,
        full_name=user.full_name,
        user_id=user.id
    )


# Альтернативный endpoint для формы OAuth2
@router.post("/login/form")
async def login_form(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(get_db)
):
    """SF-05.1: Login через форму (для Swagger UI)"""
    request = LoginRequest(email=form_data.username, password=form_data.password)
    return await login(request, db)
# Blacklist для отозванных токенов (в production используй Redis)
token_blacklist = set()

@router.post("/logout")
async def logout(
    token: str = Depends(OAuth2PasswordBearer(tokenUrl="/auth/login/form"))
):
    """
    SF-05: Выход из системы
    Добавляет токен в черный список
    """
    token_blacklist.add(token)
    return {"message": "Successfully logged out"}

# Middleware для проверки blacklist
from fastapi import HTTPException, status

async def check_token_not_blacklisted(token: str):
    if token in token_blacklist:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked"
        )


class RedirectInfo(BaseModel):
    redirect_url: str
    dashboard_component: str


@router.get("/redirect-after-login", response_model=RedirectInfo)
async def get_redirect_by_role(
        current_user: User = Depends(get_current_user)
):
    """
    SF-05.3: Возвращает URL для редиректа в зависимости от роли
    """
    role_redirects = {
        "admin": {
            "redirect_url": "/admin/dashboard",
            "dashboard_component": "AdminDashboard"
        },
        "teacher": {
            "redirect_url": "/teacher/schedule",
            "dashboard_component": "TeacherSchedule"
        },
        "student": {
            "redirect_url": "/student/schedule",
            "dashboard_component": "StudentSchedule"
        }
    }

    role = current_user.role.value
    return RedirectInfo(**role_redirects.get(role, {"redirect_url": "/", "dashboard_component": "NotFound"}))