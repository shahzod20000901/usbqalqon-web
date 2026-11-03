import io

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..deps import get_current_user
from ..hierarchy import descendant_ids
from ..models import Device, User
from ..schemas import (
    DeviceCreate,
    DeviceOut,
    DevicePage,
    DeviceUpdate,
    ImportResult,
)
from ..services.devices_import import device_to_line, parse_devices_text

router = APIRouter(prefix="/api/devices", tags=["Qurilmalar"])

GRIF_LEVELS = {
    "Nomaxfiy": 1,
    "XDFU": 2,
    "Maxfiy": 3,
    "O'ta_maxfiy": 4,
    "Mutlaqo_maxfiy": 5,
}


def _scoped_query(db: Session, current: User):
    ids = descendant_ids(db, current)
    return (
        db.query(Device)
        .options(joinedload(Device.owner))
        .filter(Device.owner_id.in_(ids))
    )


def _apply_search(query, search: str):
    pattern = f"%{search.strip()}%"
    return query.join(User, Device.owner_id == User.id).filter(
        or_(
            Device.serial_number.ilike(pattern),
            Device.vendor.ilike(pattern),
            Device.model.ilike(pattern),
            Device.grif.ilike(pattern),
            Device.device_type.ilike(pattern),
            User.username.ilike(pattern),
            User.full_name.ilike(pattern),
        )
    )


@router.get("", response_model=DevicePage, summary="Qurilmalar ro'yxati va qidiruv")
def list_devices(
    search: str | None = Query(default=None, description="Istalgan maydon bo'yicha qidiruv"),
    grif: str | None = Query(default=None),
    owner_id: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    query = _scoped_query(db, current)

    if search:
        query = _apply_search(query, search)
    if grif:
        query = query.filter(Device.grif == grif)
    if owner_id is not None:
        if owner_id not in descendant_ids(db, current):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bu foydalanuvchi qurilmalariga ruxsat yo'q",
            )
        query = query.filter(Device.owner_id == owner_id)

    total = query.count()
    items = (
        query.order_by(Device.created_at.desc(), Device.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return DevicePage(items=items, total=total, page=page, page_size=page_size)


@router.get(
    "/export",
    summary="Qurilmalarni Devices.txt formatida yuklab olish",
)
def export_devices(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    devices = (
        _scoped_query(db, current).order_by(Device.id.asc()).all()
    )
    text = "\n".join(device_to_line(device) for device in devices)
    if text:
        text += "\n"

    buffer = io.BytesIO(text.encode("utf-8"))
    return StreamingResponse(
        buffer,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="Devices.txt"'},
    )


@router.post(
    "/import",
    response_model=ImportResult,
    summary="Devices.txt faylini import qilish",
)
async def import_devices(
    file: UploadFile = File(..., description="Devices.txt formatidagi fayl"),
    owner_id: int | None = Form(default=None),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    raw = await file.read()
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fayl bo'sh",
        )
    if len(raw) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Fayl hajmi 10 MB dan oshmasligi kerak",
        )

    try:
        content = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            content = raw.decode("cp1251")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Fayl kodlashini aniqlab bo'lmadi (UTF-8 yoki CP1251 kerak)",
            )

    target_owner_id = owner_id or current.id
    if target_owner_id not in descendant_ids(db, current):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu foydalanuvchi nomidan import qilish mumkin emas",
        )

    records, errors = parse_devices_text(content)

    existing_serials = {
        row[0]
        for row in db.query(Device.serial_number)
        .filter(Device.owner_id == target_owner_id)
        .all()
    }

    imported = 0
    skipped = 0
    seen_in_file: set[str] = set()

    for record in records:
        serial = record["serial_number"]
        key = serial.lower()
        if key in seen_in_file:
            skipped += 1
            errors.append(f"Fayl ichida takrorlangan seriya: {serial}")
            continue
        seen_in_file.add(key)

        if serial in existing_serials:
            skipped += 1
            continue

        db.add(Device(owner_id=target_owner_id, **record))
        existing_serials.add(serial)
        imported += 1

    db.commit()

    return ImportResult(
        filename=file.filename or "Devices.txt",
        total_records=len(records),
        imported=imported,
        skipped=skipped,
        errors=errors[:30],
    )


@router.post(
    "",
    response_model=DeviceOut,
    status_code=status.HTTP_201_CREATED,
    summary="Yangi qurilma qo'shish",
)
def create_device(
    payload: DeviceCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    owner_id = payload.owner_id or current.id
    if owner_id not in descendant_ids(db, current):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu foydalanuvchi nomidan qurilma qo'shish mumkin emas",
        )

    duplicate = (
        db.query(Device)
        .filter(
            Device.owner_id == owner_id,
            Device.serial_number == payload.serial_number,
        )
        .first()
    )
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu seriya raqami ushbu bo'limda allaqachon mavjud",
        )

    device = Device(owner_id=owner_id, **payload.model_dump(exclude={"owner_id"}))
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


@router.get("/{device_id}", response_model=DeviceOut, summary="Bitta qurilma")
def get_device(
    device_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    device = _scoped_query(db, current).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Qurilma topilmadi",
        )
    return device


@router.put("/{device_id}", response_model=DeviceOut, summary="Qurilmani tahrirlash")
def update_device(
    device_id: int,
    payload: DeviceUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    device = _scoped_query(db, current).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Qurilma topilmadi",
        )

    data = payload.model_dump(exclude_unset=True)

    new_owner_id = data.get("owner_id", device.owner_id)
    if new_owner_id not in descendant_ids(db, current):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Qurilmani bu foydalanuvchiga o'tkazish mumkin emas",
        )

    new_serial = data.get("serial_number", device.serial_number)
    duplicate = (
        db.query(Device)
        .filter(
            Device.owner_id == new_owner_id,
            Device.serial_number == new_serial,
            Device.id != device.id,
        )
        .first()
    )
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu seriya raqami ushbu bo'limda allaqachon mavjud",
        )

    for field, value in data.items():
        setattr(device, field, value)

    db.add(device)
    db.commit()
    db.refresh(device)
    return device


@router.delete(
    "/{device_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Qurilmani o'chirish",
)
def delete_device(
    device_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    device = _scoped_query(db, current).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Qurilma topilmadi",
        )

    db.delete(device)
    db.commit()
    return None
