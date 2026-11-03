"""Foydalanuvchilar ierarxiyasi bo'yicha ruxsatlar."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from .models import User


def is_admin(user: User) -> bool:
    return bool(user.is_superuser)


def all_user_ids(db: Session) -> set[int]:
    return {row[0] for row in db.query(User.id).all()}


def descendant_ids(db: Session, user: User) -> set[int]:
    """Foydalanuvchining o'zini va barcha bolalarini (rekursiv) qaytaradi."""
    if is_admin(user):
        return all_user_ids(db)

    result: set[int] = set()
    queue: list[int] = [user.id]

    while queue:
        current_id = queue.pop()
        if current_id in result:
            continue
        result.add(current_id)
        children = (
            db.query(User.id).filter(User.parent_id == current_id).all()
        )
        queue.extend(child[0] for child in children)

    return result


def get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Foydalanuvchi topilmadi",
        )
    return user


def ensure_visible(db: Session, current: User, target: User) -> None:
    if target.id not in descendant_ids(db, current):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu foydalanuvchi ma'lumotlariga ruxsat yo'q",
        )


def ensure_can_assign_parent(
    db: Session, current: User, parent_id: int | None
) -> User | None:
    """Yangi/o'zgartirilayotgan foydalanuvchi uchun ota validligini tekshiradi."""
    if parent_id is None:
        if not is_admin(current):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Faqat administrator ildiz foydalanuvchi yarata oladi",
            )
        return None

    parent = get_user_or_404(db, parent_id)
    if parent.id not in descendant_ids(db, current):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bu ota ostiga foydalanuvchi qo'shish mumkin emas",
        )
    return parent


def ensure_no_cycle(db: Session, target: User, new_parent_id: int | None) -> None:
    """Foydalanuvchini o'z avlodiga ota qilib qo'yishning oldini oladi."""
    if new_parent_id is None:
        return
    if new_parent_id == target.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Foydalanuvchi o'ziga ota bo'la olmaydi",
        )
    target_subtree = descendant_ids(db, target)
    if new_parent_id in target_subtree:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sikl hosil bo'ladi: ota sifatida o'z avlodini tanlash mumkin emas",
        )
