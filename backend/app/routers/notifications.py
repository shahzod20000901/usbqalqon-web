from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import BlacklistEntry, Notification, User
from ..schemas import (
    NotificationCount,
    NotificationOut,
    NotificationPage,
)

router = APIRouter(prefix="/api/notifications", tags=["Bildirishnomalar"])


def _base_query(db: Session, current: User):
    return db.query(Notification).filter(Notification.user_id == current.id)


def _unread_count(db: Session, current: User) -> int:
    return (
        _base_query(db, current)
        .filter(Notification.is_read.is_(False))
        .count()
    )


def _mark_reviewed(db: Session, entry_ids: set[int]) -> None:
    """Bildirishnoma o'qilganda bog'langan hodisani ko'rib chiqilgan qiladi."""
    if not entry_ids:
        return
    db.query(BlacklistEntry).filter(
        BlacklistEntry.id.in_(entry_ids),
        BlacklistEntry.status == "yangi",
    ).update(
        {BlacklistEntry.status: "korildi"},
        synchronize_session=False,
    )


@router.get(
    "",
    response_model=NotificationPage,
    summary="Bildirishnomalar ro'yxati",
)
def list_notifications(
    unread_only: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    query = _base_query(db, current)
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))

    total = query.count()
    items = (
        query.order_by(Notification.created_at.desc(), Notification.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return NotificationPage(
        items=items,
        total=total,
        unread=_unread_count(db, current),
        page=page,
        page_size=page_size,
    )


@router.get(
    "/unread-count",
    response_model=NotificationCount,
    summary="O'qilmagan bildirishnomalar soni",
)
def unread_count(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    return NotificationCount(unread=_unread_count(db, current))


@router.post(
    "/read-all",
    response_model=NotificationCount,
    summary="Barcha bildirishnomalarni o'qilgan deb belgilash",
)
def mark_all_read(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    unread_query = _base_query(db, current).filter(Notification.is_read.is_(False))
    entry_ids = {
        row[0]
        for row in unread_query.with_entities(Notification.blacklist_entry_id)
        .filter(Notification.blacklist_entry_id.isnot(None))
        .all()
    }
    _mark_reviewed(db, entry_ids)
    unread_query.update(
        {Notification.is_read: True}, synchronize_session=False
    )
    db.commit()
    return NotificationCount(unread=0)


@router.post(
    "/{notification_id}/read",
    response_model=NotificationOut,
    summary="Bildirishnomani o'qilgan deb belgilash",
)
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    notification = (
        _base_query(db, current)
        .filter(Notification.id == notification_id)
        .first()
    )
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bildirishnoma topilmadi",
        )

    notification.is_read = True
    if notification.blacklist_entry_id:
        _mark_reviewed(db, {notification.blacklist_entry_id})
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Bildirishnomani o'chirish",
)
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    notification = (
        _base_query(db, current)
        .filter(Notification.id == notification_id)
        .first()
    )
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bildirishnoma topilmadi",
        )

    db.delete(notification)
    db.commit()
    return None
