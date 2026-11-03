from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..deps import get_current_user
from ..hierarchy import descendant_ids
from ..models import BlacklistEntry, Notification, User
from ..schemas import (
    BlacklistCreate,
    BlacklistOut,
    BlacklistPage,
)
from ..services.notifications import notify_blacklist_entry

router = APIRouter(prefix="/api/blacklist", tags=["Qora ro'yxat"])


def _scoped_query(db: Session, current: User):
    ids = descendant_ids(db, current)
    return (
        db.query(BlacklistEntry)
        .options(joinedload(BlacklistEntry.owner))
        .filter(BlacklistEntry.owner_id.in_(ids))
    )


@router.get(
    "",
    response_model=BlacklistPage,
    summary="Qora ro'yxat: qidiruv va filtrlash",
)
def list_blacklist(
    search: str | None = Query(
        default=None,
        description="Seriya, ishlab chiqaruvchi, model, grif, sabab, agent yoki egasi",
    ),
    status_filter: str | None = Query(default=None, alias="status"),
    owner_id: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    query = _scoped_query(db, current)

    if search:
        pattern = f"%{search.strip()}%"
        query = query.join(User, BlacklistEntry.owner_id == User.id).filter(
            or_(
                BlacklistEntry.serial_number.ilike(pattern),
                BlacklistEntry.vendor.ilike(pattern),
                BlacklistEntry.model.ilike(pattern),
                BlacklistEntry.grif.ilike(pattern),
                BlacklistEntry.device_type.ilike(pattern),
                BlacklistEntry.reason.ilike(pattern),
                BlacklistEntry.agent_name.ilike(pattern),
                BlacklistEntry.status.ilike(pattern),
                User.username.ilike(pattern),
                User.full_name.ilike(pattern),
            )
        )

    if status_filter:
        query = query.filter(BlacklistEntry.status == status_filter)

    if owner_id is not None:
        if owner_id not in descendant_ids(db, current):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bu foydalanuvchi qora ro'yxatiga ruxsat yo'q",
            )
        query = query.filter(BlacklistEntry.owner_id == owner_id)

    total = query.count()
    items = (
        query.order_by(
            BlacklistEntry.last_seen_at.desc(), BlacklistEntry.id.desc()
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return BlacklistPage(
        items=items, total=total, page=page, page_size=page_size
    )


@router.post(
    "",
    response_model=BlacklistOut,
    status_code=status.HTTP_201_CREATED,
    summary="Qora ro'yxatga yozuv qo'shish",
)
def create_blacklist_entry(
    payload: BlacklistCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    owner_id = payload.owner_id or current.id
    if owner_id not in descendant_ids(db, current):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu foydalanuvchi nomidan yozuv qo'shish mumkin emas",
        )

    duplicate = (
        db.query(BlacklistEntry)
        .filter(
            BlacklistEntry.owner_id == owner_id,
            BlacklistEntry.serial_number == payload.serial_number,
        )
        .first()
    )
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu qurilma ushbu bo'lim qora ro'yxatida allaqachon mavjud",
        )

    entry = BlacklistEntry(
        owner_id=owner_id,
        **payload.model_dump(exclude={"owner_id"}),
    )
    db.add(entry)
    db.flush()

    owner = db.get(User, owner_id)
    if owner:
        notify_blacklist_entry(db, entry, owner, agent_name=payload.agent_name)

    db.commit()
    db.refresh(entry)
    return entry


@router.get("/{entry_id}", response_model=BlacklistOut, summary="Bitta yozuv")
def get_blacklist_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    entry = (
        _scoped_query(db, current)
        .filter(BlacklistEntry.id == entry_id)
        .first()
    )
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Yozuv topilmadi",
        )
    return entry


@router.post(
    "/{entry_id}/review",
    response_model=BlacklistOut,
    summary="Hodisani ko'rib chiqilgan deb belgilash",
    description=(
        "Yozuvni tahrirlamaydi, faqat holatini `korildi` ga o'zgartiradi va "
        "joriy foydalanuvchining shu yozuvga tegishli bildirishnomalarini "
        "o'qilgan deb belgilaydi."
    ),
)
def review_blacklist_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    entry = (
        _scoped_query(db, current)
        .filter(BlacklistEntry.id == entry_id)
        .first()
    )
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Yozuv topilmadi",
        )

    if entry.status == "yangi":
        entry.status = "korildi"
        db.add(entry)

    db.query(Notification).filter(
        Notification.user_id == current.id,
        Notification.blacklist_entry_id == entry.id,
        Notification.is_read.is_(False),
    ).update({Notification.is_read: True}, synchronize_session=False)

    db.commit()
    db.refresh(entry)
    return entry


@router.delete(
    "/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Qora ro'yxat yozuvini o'chirish",
)
def delete_blacklist_entry(
    entry_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    entry = (
        _scoped_query(db, current)
        .filter(BlacklistEntry.id == entry_id)
        .first()
    )
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Yozuv topilmadi",
        )

    db.delete(entry)
    db.commit()
    return None
