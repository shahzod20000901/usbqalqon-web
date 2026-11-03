"""Qora ro'yxat hodisalari bo'yicha administratorga bildirishnoma yuborish."""

from sqlalchemy.orm import Session

from ..models import BlacklistEntry, Notification, User


def ancestor_ids(db: Session, user: User) -> list[int]:
    """Foydalanuvchining yuqori bo'limlarini (yuqoriga qarab) qaytaradi."""
    result: list[int] = []
    seen: set[int] = set()
    parent_id = user.parent_id

    while parent_id is not None and parent_id not in seen:
        seen.add(parent_id)
        result.append(parent_id)
        parent = db.get(User, parent_id)
        if not parent:
            break
        parent_id = parent.parent_id

    return result


def notification_recipient_ids(db: Session, owner: User) -> set[int]:
    """Faol administratorlarni qaytaradi.

    Administratorlar mavjud bo'lmasa, zaxira sifatida yuqori bo'limlarga
    yuboriladi.
    """
    recipients = {
        row[0]
        for row in db.query(User.id)
        .filter(User.is_superuser.is_(True), User.is_active.is_(True))
        .all()
    }
    if not recipients:
        recipients.update(ancestor_ids(db, owner))
    return recipients


def notify_blacklist_entry(
    db: Session,
    entry: BlacklistEntry,
    owner: User,
    *,
    agent_name: str = "",
) -> int:
    """Yangi qora ro'yxat yozuvi haqida administratorga xabar yaratadi.

    Yozuv `db.flush()` qilingan bo'lishi kerak (id mavjud bo'lishi uchun).
    Chaqiruvchi tomonidan `db.commit()` qilinadi.
    """
    recipients = notification_recipient_ids(db, owner)
    if not recipients:
        return 0

    device = " ".join(part for part in (entry.vendor, entry.model) if part).strip()
    device_text = device or entry.device_type or "USB qurilma"
    department = owner.full_name or owner.username
    agent_text = agent_name or entry.agent_name or "noma'lum kompyuter"

    title = "Yangi ruxsat etilmagan qurilma"
    message = (
        f"{department} tomonidan ro'yxatda bo'lmagan qurilma aniqlandi: "
        f"{device_text} (seriya: {entry.serial_number}). "
        f"Agent: {agent_text}. Seriya bo'lim qora ro'yxatiga qo'shildi."
    )

    created = 0
    for user_id in sorted(recipients):
        db.add(
            Notification(
                user_id=user_id,
                title=title,
                message=message,
                kind="blacklist",
                blacklist_entry_id=entry.id,
                is_read=False,
            )
        )
        created += 1

    return created
