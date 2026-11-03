from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .config import settings
from .database import SessionLocal, get_db, init_db
from .models import User
from .routers import (
    agent,
    auth,
    blacklist,
    devices,
    notifications,
    software,
    stats,
    users,
)
from .security import decode_access_token
from .seed import ensure_admin

OPENAPI_TAGS = [
    {
        "name": "Autentifikatsiya",
        "description": "JWT orqali tizimga kirish va joriy foydalanuvchi.",
    },
    {
        "name": "Foydalanuvchilar",
        "description": "Foydalanuvchilar ierarxiyasi va CRUD amallari.",
    },
    {
        "name": "Qurilmalar",
        "description": "Ruxsat etilgan qurilmalar, qidiruv va Devices.txt import/export.",
    },
    {
        "name": "Qora ro'yxat",
        "description": "Ro'yxatda bo'lmagan qurilmalar CRUD amallari.",
    },
    {
        "name": "Agent API",
        "description": (
            "Desktop agent uchun API. `X-Agent-Token` sarlavhasi orqali "
            "autentifikatsiya qilinadi. Agent tomonidan aniqlangan ruxsat "
            "etilmagan qurilmalar avtomatik qora ro'yxatga yoziladi."
        ),
    },
    {
        "name": "Bildirishnomalar",
        "description": (
            "Administrator uchun yangi qora ro'yxat hodisalari haqidagi "
            "bildirishnomalar."
        ),
    },
    {
        "name": "Dasturiy ta'minot",
        "description": (
            "Superadmin yuklagan yagona agent `.exe` paketini yuklab olish, "
            "shaxsiy agent tokenini ko'rish va yangilash."
        ),
    },
    {
        "name": "Statistika",
        "description": "Bosh sahifa uchun jamlangan ko'rsatkichlar.",
    },
]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    with SessionLocal() as db:
        ensure_admin(db)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "USB Qalqon desktop dasturining web qismi.\n\n"
        "Tizim tashkiliy tuzilmadagi foydalanuvchilarni, ularning "
        "ruxsat etilgan qurilmalarini va qora ro'yxat hodisalarini saqlaydi."
    ),
    openapi_tags=OPENAPI_TAGS,
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _verify_docs_superuser(
    token: str | None = Query(default=None),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    raw_token = token
    if not raw_token and authorization and authorization.startswith("Bearer "):
        raw_token = authorization.split(" ", 1)[1]

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Faqat administrator uchun ruxsat etilgan",
        )

    payload = decode_access_token(raw_token)
    if not payload or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token yaroqsiz yoki muddati tugagan",
        )

    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Token yaroqsiz"
        )

    user = db.get(User, user_id)
    if not user or not user.is_active or not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API hujjatlar faqat administrator uchun ruxsat etilgan",
        )
    return user


@app.get("/openapi.json", include_in_schema=False)
def get_custom_openapi(
    token: str | None = Query(default=None),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _verify_docs_superuser(token=token, authorization=authorization, db=db)
    return get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
    )


@app.get("/docs", include_in_schema=False)
def custom_swagger_ui(
    token: str | None = Query(default=None),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _verify_docs_superuser(token=token, authorization=authorization, db=db)
    openapi_url = f"/openapi.json?token={token}" if token else "/openapi.json"
    return get_swagger_ui_html(
        openapi_url=openapi_url,
        title=f"{app.title} — API hujjati",
        swagger_js_url="/static/swagger/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger/swagger-ui.css",
        swagger_favicon_url="/static/swagger/favicon-32x32.png",
    )


@app.get("/redoc", include_in_schema=False)
def custom_redoc(
    token: str | None = Query(default=None),
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    _verify_docs_superuser(token=token, authorization=authorization, db=db)
    openapi_url = f"/openapi.json?token={token}" if token else "/openapi.json"
    return get_redoc_html(
        openapi_url=openapi_url,
        title=f"{app.title} — ReDoc",
        redoc_js_url="/static/swagger/swagger-ui-bundle.js",
    )


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(devices.router)
app.include_router(blacklist.router)
app.include_router(agent.router)
app.include_router(notifications.router)
app.include_router(software.router)
app.include_router(stats.router)


@app.get("/", tags=["Root"], summary="API haqida ma'lumot")
def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/api/health",
    }


@app.get("/api/health", tags=["Root"], summary="Health check")
def health():
    return {"status": "ok"}
