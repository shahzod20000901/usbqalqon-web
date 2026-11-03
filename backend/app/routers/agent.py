from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_agent_user
from ..hierarchy import descendant_ids
from ..models import BlacklistEntry, Device, User, utcnow
from ..schemas import (
    AgentCheckResult,
    AgentDevice,
    AgentDeviceCreate,
    AgentDeviceUpdate,
    AgentHeartbeat,
    AgentLoginRequest,
    AgentLoginResponse,
    AgentReport,
    AgentReportResult,
    BlacklistOut,
)
from ..security import create_access_token, generate_agent_token, verify_password
from ..services.notifications import notify_blacklist_entry

router = APIRouter(prefix="/api/agent", tags=["Agent API"])


@router.post(
    "/login",
    response_model=AgentLoginResponse,
    summary="Agent uchun login va parol orqali autentifikatsiya",
    description=(
        "Desktop agent superadmin tomonidan yaratilgan login va parol bilan "
        "tizimga kiradi va o'zining shaxsiy tokenlarini oladi."
    ),
)
def agent_login(
    payload: AgentLoginRequest,
    db: Session = Depends(get_db),
):
    username = payload.username.strip()
    user = db.query(User).filter(User.username == username).first()

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login yoki parol noto'g'ri",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Foydalanuvchi hisobi faol emas",
        )

    if not user.agent_token:
        user.agent_token = generate_agent_token()
        db.add(user)
        db.commit()
        db.refresh(user)

    return AgentLoginResponse(
        access_token=create_access_token(user.id),
        token_type="bearer",
        agent_token=user.agent_token,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        is_superuser=bool(user.is_superuser),
        server_time=datetime.utcnow(),
    )


def _agent_device(device: Device) -> AgentDevice:
    return AgentDevice(
        serial_number=device.serial_number,
        vendor=device.vendor,
        model=device.model,
        grif=device.grif,
        device_type=device.device_type,
        owner_username=device.owner.username if device.owner else "",
        owner_full_name=device.owner.full_name if device.owner else "",
    )


@router.post(
    "/blacklist",
    response_model=AgentReportResult,
    summary="Desktop agentdan ruxsat etilmagan qurilma xabarini qabul qilish",
    description=(
        "Desktop agent `X-Agent-Token` sarlavhasi orqali autentifikatsiya qiladi. "
        "Agar shu seriya raqamli yozuv allaqachon mavjud bo'lsa, u yangilanadi "
        "va `event_count` oshiriladi."
    ),
)
def report_blacklist(
    payload: AgentReport,
    db: Session = Depends(get_db),
    agent: User = Depends(get_agent_user),
):
    serial = payload.serial_number.strip()
    if not serial:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seriya raqami bo'sh bo'lishi mumkin emas",
        )

    entry = (
        db.query(BlacklistEntry)
        .filter(
            BlacklistEntry.owner_id == agent.id,
            BlacklistEntry.serial_number == serial,
        )
        .first()
    )

    now = utcnow()
    created = entry is None

    if entry is None:
        entry = BlacklistEntry(
            owner_id=agent.id,
            serial_number=serial,
            vendor=payload.vendor,
            model=payload.model,
            grif=payload.grif,
            device_type=payload.device_type,
            reason=payload.reason or "Ro'yxatda bo'lmagan qurilma aniqlandi",
            status="yangi",
            agent_name=payload.agent_name,
            event_count=1,
            first_seen_at=now,
            last_seen_at=now,
        )
        db.add(entry)
        db.flush()
        notify_blacklist_entry(db, entry, agent, agent_name=payload.agent_name)
    else:
        entry.event_count += 1
        entry.last_seen_at = now
        entry.agent_name = payload.agent_name or entry.agent_name
        if payload.vendor:
            entry.vendor = payload.vendor
        if payload.model:
            entry.model = payload.model
        if payload.grif:
            entry.grif = payload.grif
        if payload.device_type:
            entry.device_type = payload.device_type
        if payload.reason:
            entry.reason = payload.reason

    db.commit()
    db.refresh(entry)

    return AgentReportResult(
        created=created,
        entry=BlacklistOut.model_validate(entry),
    )


@router.get(
    "/devices",
    response_model=list[AgentDevice],
    summary="Agent uchun ruxsat etilgan qurilmalar ro'yxati",
    description=(
        "Desktop agent o'zining va unga tegishli bo'limlarning ruxsat etilgan "
        "qurilmalar ro'yxatini oladi. Bu ro'yxat lokal `Devices.txt` bilan "
        "sinxronlash uchun ishlatiladi."
    ),
)
def list_agent_devices(
    db: Session = Depends(get_db),
    agent: User = Depends(get_agent_user),
):
    ids = descendant_ids(db, agent)
    devices = (
        db.query(Device)
        .filter(Device.owner_id.in_(ids))
        .order_by(Device.serial_number.asc())
        .all()
    )
    return [_agent_device(device) for device in devices]


@router.post(
    "/devices",
    response_model=AgentDevice,
    status_code=status.HTTP_201_CREATED,
    summary="Desktop agentdan ruxsat etilgan qurilmani ro'yxatga qo'shish",
    description=(
        "Agar shu seriya raqamli qurilma agentga tegishli bo'limda mavjud "
        "bo'lsa, uning ma'lumotlari yangilanadi (upsert)."
    ),
)
def register_agent_device(
    payload: AgentDeviceCreate,
    db: Session = Depends(get_db),
    agent: User = Depends(get_agent_user),
):
    serial = payload.serial_number.strip()
    device = (
        db.query(Device)
        .filter(Device.owner_id == agent.id, Device.serial_number == serial)
        .first()
    )

    if device is None:
        device = Device(owner_id=agent.id, **payload.model_dump())
        db.add(device)
    else:
        for field, value in payload.model_dump(exclude={"serial_number"}).items():
            setattr(device, field, value)
        db.add(device)

    db.commit()
    db.refresh(device)
    return _agent_device(device)


@router.put(
    "/devices/{serial_number}",
    response_model=AgentDevice,
    summary="Desktop agentdan qurilma ma'lumotlarini yangilash",
)
def update_agent_device(
    serial_number: str,
    payload: AgentDeviceUpdate,
    db: Session = Depends(get_db),
    agent: User = Depends(get_agent_user),
):
    serial = serial_number.strip()
    device = (
        db.query(Device)
        .filter(Device.owner_id == agent.id, Device.serial_number == serial)
        .first()
    )
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Qurilma topilmadi",
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(device, field, value)

    db.add(device)
    db.commit()
    db.refresh(device)
    return _agent_device(device)


@router.delete(
    "/devices/{serial_number}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Desktop agentdan qurilmani o'chirish",
)
def delete_agent_device(
    serial_number: str,
    db: Session = Depends(get_db),
    agent: User = Depends(get_agent_user),
):
    serial = serial_number.strip()
    device = (
        db.query(Device)
        .filter(Device.owner_id == agent.id, Device.serial_number == serial)
        .first()
    )
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Qurilma topilmadi",
        )

    db.delete(device)
    db.commit()
    return None


@router.get(
    "/check/{serial_number}",
    response_model=AgentCheckResult,
    summary="Seriya raqami ruxsat etilgan qurilmalar bazasida borligini tekshirish",
)
def check_device(
    serial_number: str,
    db: Session = Depends(get_db),
    agent: User = Depends(get_agent_user),
):
    serial = serial_number.strip()
    ids = descendant_ids(db, agent)

    device = (
        db.query(Device)
        .filter(
            Device.owner_id.in_(ids),
            Device.serial_number == serial,
        )
        .first()
    )

    return AgentCheckResult(
        serial_number=serial,
        allowed=device is not None,
        registered=device is not None,
        grif=device.grif if device else "",
        owner_username=device.owner.username if device and device.owner else "",
        owner_full_name=device.owner.full_name if device and device.owner else "",
    )


@router.post(
    "/heartbeat",
    response_model=AgentHeartbeat,
    summary="Agent aloqasini tekshirish",
)
def heartbeat(agent: User = Depends(get_agent_user)):
    return AgentHeartbeat(
        ok=True,
        username=agent.username,
        full_name=agent.full_name,
        server_time=datetime.utcnow(),
    )
