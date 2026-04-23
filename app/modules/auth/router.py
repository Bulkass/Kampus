from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from pydantic import BaseModel, EmailStr

from app.core.database import get_db
from app.core.models import User
from app.core.security import (
    verify_password,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    decode_token,
    get_password_hash
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ============================================
# СХЕМЫ
# ============================================

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    full_name: str
    user_id: int


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserInfo(BaseModel):
    id: int
    email: str
    full_name: str
    role: str


class RedirectInfo(BaseModel):
    redirect_url: str
    dashboard_component: str


# ============================================
# ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ
# ============================================

token_blacklist = set()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login/form")


# ============================================
# ЗАВИСИМОСТЬ: Получение текущего пользователя
# ============================================

async def get_current_user_dependency(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db)
) -> User:
    """Зависимость для получения текущего пользователя из токена"""

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
            detail="Недействительный токен",
            headers={"WWW-Authenticate": "Bearer"},
        )

    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Некорректный токен"
        )

    # Поиск пользователя
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт деактивирован"
        )

    return user


# ============================================
# SF-05.1: LOGIN
# ============================================

@router.post("/login", response_model=TokenResponse)
async def login(
        request: LoginRequest,
        db: Session = Depends(get_db)
):
    """SF-05.1: Аутентификация пользователя"""

    user = db.query(User).filter(User.email == request.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль"
        )

    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Аккаунт деактивирован"
        )

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


# ============================================
# SF-05.1: LOGIN FORM (для Swagger)
# ============================================

@router.post("/login/form", response_model=TokenResponse)
async def login_form(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: Session = Depends(get_db)
):
    """Login через форму (Swagger UI)"""
    request = LoginRequest(
        email=form_data.username,
        password=form_data.password
    )
    return await login(request, db)


# ============================================
# SF-05: LOGOUT
# ============================================

@router.post("/logout")
async def logout(
        token: str = Depends(oauth2_scheme)
):
    """SF-05: Выход из системы"""
    token_blacklist.add(token)
    return {"message": "Successfully logged out"}


# ============================================
# GET CURRENT USER INFO
# ============================================

@router.get("/me", response_model=UserInfo)
async def get_current_user_info(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db)
):
    """Получение информации о текущем пользователе"""

    if token in token_blacklist:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен отозван"
        )

    payload = decode_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Недействительный токен"
        )

    email = payload.get("sub")
    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден"
        )

    return UserInfo(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value
    )


# ============================================
# SF-05.3: РЕДИРЕКТ ПО РОЛИ
# ============================================

@router.get("/redirect-after-login", response_model=RedirectInfo)
async def get_redirect_by_role(
        current_user: User = Depends(get_current_user_dependency)
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
    redirect_data = role_redirects.get(role)

    if not redirect_data:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Неизвестная роль: {role}"
        )

    return RedirectInfo(**redirect_data)


# ============================================
# ВСПОМОГАТЕЛЬНЫЕ ЭНДПОИНТЫ
# ============================================

@router.post("/create-test-user")
async def create_test_user(
        email: str,
        password: str,
        full_name: str,
        role: str = "student",
        db: Session = Depends(get_db)
):
    """Создание тестового пользователя (только для разработки)"""
    from app.core.models import UserRole

    if role not in ["student", "teacher", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Недопустимая роль"
        )

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь уже существует"
        )

    user = User(
        email=email,
        password_hash=get_password_hash(password),
        full_name=full_name,
        role=UserRole(role),
        is_active=True
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "message": f"Пользователь {email} создан",
        "id": user.id,
        "role": user.role.value
    }