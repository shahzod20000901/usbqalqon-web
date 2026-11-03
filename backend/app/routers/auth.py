from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import ChangePasswordRequest, TokenResponse, UserOut
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["Autentifikatsiya"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Tizimga kirish (JWT token olish)",
)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == form_data.username).first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login yoki parol noto'g'ri",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Foydalanuvchi faol emas",
        )

    return TokenResponse(
        access_token=create_access_token(user.id),
        agent_token=user.agent_token or "",
        user=UserOut.model_validate(user),
    )


@router.get(
    "/me",
    response_model=UserOut,
    summary="Joriy foydalanuvchi ma'lumotlari",
)
def read_me(current: User = Depends(get_current_user)):
    return current


@router.post(
    "/change-password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="O'z parolini almashtirish",
)
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    if not verify_password(payload.old_password, current.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Eski parol noto'g'ri",
        )

    current.password_hash = hash_password(payload.new_password)
    db.add(current)
    db.commit()
    return None
