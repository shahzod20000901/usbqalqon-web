"""Dasturiy ta'minot: superadmin yuklagan yagona agent (.exe) tarqatish."""

import hashlib
from datetime import datetime
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_admin, get_current_user
from ..models import AgentPackage, User
from ..schemas import AgentPackageOut, SoftwareInfo
from ..security import generate_agent_token

router = APIRouter(prefix="/api/software", tags=["Dasturiy ta'minot"])

POLL_SECONDS = 10
ALLOWED_EXTENSIONS = {".exe"}


def _base_url(request: Request) -> str:
    if settings.server_url:
        return settings.server_url.rstrip("/")
    return str(request.base_url).rstrip("/")


def _agent_dir() -> Path:
    path = Path(settings.agent_dir)
    if not path.is_absolute():
        path = Path.cwd() / path
    path.mkdir(parents=True, exist_ok=True)
    return path


def _latest_package(db: Session) -> AgentPackage | None:
    return (
        db.query(AgentPackage)
        .order_by(AgentPackage.uploaded_at.desc(), AgentPackage.id.desc())
        .first()
    )


def _package_out(package: AgentPackage | None, base: str) -> AgentPackageOut | None:
    if not package:
        return None
    return AgentPackageOut(
        id=package.id,
        original_filename=package.original_filename,
        version=package.version,
        size=package.size,
        sha256=package.sha256,
        uploaded_at=package.uploaded_at,
        download_url=f"{base}/api/software/package/download",
    )


def _software_info(request: Request, current: User, db: Session) -> SoftwareInfo:
    base = _base_url(request)
    return SoftwareInfo(
        username=current.username,
        full_name=current.full_name,
        server_url=base,
        docs_url=f"{base}/docs",
        agent_token=current.agent_token,
        poll_seconds=POLL_SECONDS,
        is_superuser=bool(current.is_superuser),
        package=_package_out(_latest_package(db), base),
    )


def _delete_package_file(package: AgentPackage) -> None:
    try:
        path = _agent_dir() / package.stored_filename
        if path.exists():
            path.unlink()
    except OSError:
        pass


@router.get(
    "/info",
    response_model=SoftwareInfo,
    summary="Agent paketi, server manzili va shaxsiy token haqida ma'lumot",
)
def software_info(
    request: Request,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    return _software_info(request, current, db)


@router.post(
    "/token/rotate",
    response_model=SoftwareInfo,
    summary="Agent tokenini yangilash (eskisi bekor qilinadi)",
)
def rotate_agent_token(
    request: Request,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    current.agent_token = generate_agent_token()
    db.add(current)
    db.commit()
    db.refresh(current)
    return _software_info(request, current, db)


@router.get(
    "/package",
    response_model=AgentPackageOut | None,
    summary="Yuklangan agent paketi haqida ma'lumot",
)
def package_info(
    request: Request,
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    return _package_out(_latest_package(db), _base_url(request))


@router.post(
    "/package",
    response_model=AgentPackageOut,
    status_code=status.HTTP_201_CREATED,
    summary="Agent .exe faylini yuklash (faqat superadmin)",
    description=(
        "Yangi agent `.exe` faylini yuklaydi. Avvalgi paket avtomatik "
        "almashtiriladi. Fayl Windows PE (MZ) formatida bo'lishi tekshiriladi."
    ),
)
async def upload_package(
    request: Request,
    file: UploadFile = File(..., description="Windows .exe agent fayli"),
    version: str = Form(default=""),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_admin),
):
    original_name = Path(file.filename or "USBQalqonAgent.exe").name
    extension = Path(original_name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Faqat .exe fayl yuklash mumkin",
        )

    max_bytes = max(1, settings.max_agent_package_mb) * 1024 * 1024
    agent_dir = _agent_dir()
    stored_name = f"USBQalqonAgent-{datetime.now():%Y%m%d%H%M%S}.exe"
    target = agent_dir / stored_name

    digest = hashlib.sha256()
    size = 0
    first_chunk = True

    try:
        with target.open("wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                if first_chunk:
                    first_chunk = False
                    if not chunk.startswith(b"MZ"):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Fayl Windows .exe formatida emas (MZ sarlavhasi topilmadi)",
                        )
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=(
                            f"Fayl hajmi {settings.max_agent_package_mb} MB dan "
                            "oshmasligi kerak"
                        ),
                    )
                digest.update(chunk)
                out.write(chunk)
    except HTTPException:
        target.unlink(missing_ok=True)
        raise
    except OSError as error:
        target.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Faylni saqlab bo'lmadi: {error}",
        )
    finally:
        await file.close()

    if size == 0:
        target.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fayl bo'sh",
        )

    previous = _latest_package(db)
    if previous:
        _delete_package_file(previous)
        db.delete(previous)
        db.flush()

    package = AgentPackage(
        original_filename=original_name,
        stored_filename=stored_name,
        version=(version or "").strip()[:64] or datetime.now().strftime("%Y.%m.%d"),
        size=size,
        sha256=digest.hexdigest(),
        uploaded_by_id=current.id,
        uploaded_at=datetime.utcnow(),
    )
    db.add(package)
    db.commit()
    db.refresh(package)

    return _package_out(package, _base_url(request))


@router.get(
    "/package/download",
    summary="Agent .exe faylini yuklab olish",
    response_class=FileResponse,
)
def download_package(
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_user),
):
    package = _latest_package(db)
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent paketi hali yuklanmagan. Administratorga murojaat qiling.",
        )

    path = _agent_dir() / package.stored_filename
    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent fayli diskda topilmadi. Iltimos, qayta yuklang.",
        )

    return FileResponse(
        path,
        media_type="application/vnd.microsoft.portable-executable",
        filename=package.original_filename,
        headers={"X-Checksum-Sha256": package.sha256},
    )


@router.delete(
    "/package",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Agent paketini o'chirish (faqat superadmin)",
)
def delete_package(
    db: Session = Depends(get_db),
    _current: User = Depends(get_current_admin),
):
    package = _latest_package(db)
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent paketi topilmadi",
        )

    _delete_package_file(package)
    db.delete(package)
    db.commit()
    return None
