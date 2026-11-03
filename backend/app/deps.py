from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .security import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)
agent_key_header = APIKeyHeader(name="X-Agent-Token", auto_error=False)

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Token yaroqsiz yoki muddati tugagan",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        raise credentials_exception

    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        raise credentials_exception

    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise credentials_exception

    return user


def get_current_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu amal faqat administrator uchun",
        )
    return user


def get_agent_user(
    agent_token: str | None = Security(agent_key_header),
    bearer_token: str | None = Security(oauth2_scheme_optional),
    db: Session = Depends(get_db),
) -> User:
    user: User | None = None

    if agent_token:
        user = (
            db.query(User)
            .filter(User.agent_token == agent_token, User.is_active.is_(True))
            .first()
        )

    if not user and bearer_token:
        payload = decode_access_token(bearer_token)
        if payload and payload.get("sub"):
            try:
                user_id = int(payload["sub"])
                user = db.get(User, user_id)
                if user and not user.is_active:
                    user = None
            except (TypeError, ValueError):
                user = None

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autentifikatsiya qilinmagan. X-Agent-Token yoki Authorization Bearer token talab qilinadi",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
