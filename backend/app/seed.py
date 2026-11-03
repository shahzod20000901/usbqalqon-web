"""Boshlang'ich ma'lumotlar: administrator va (ixtiyoriy) demo ierarxiya."""

import argparse

from sqlalchemy.orm import Session

from .config import settings
from .database import SessionLocal, init_db
from .models import BlacklistEntry, Device, User
from .security import generate_agent_token, hash_password


def ensure_admin(db: Session) -> User:
    user = db.query(User).filter(User.username == settings.admin_username).first()
    if user:
        return user

    user = User(
        username=settings.admin_username,
        full_name=settings.admin_full_name,
        role="admin",
        password_hash=hash_password(settings.admin_password),
        agent_token=generate_agent_token(),
        is_active=True,
        is_superuser=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    print(f"[seed] Administrator yaratildi: {user.username}")
    return user


def seed_demo(db: Session) -> None:
    if db.query(User).count() > 1:
        print("[seed] Demo ma'lumotlar allaqachon mavjud, o'tkazib yuborildi.")
        return

    admin = ensure_admin(db)

    rahbar = User(
        username="rahbar",
        full_name="Bo'lim rahbari",
        role="rahbar",
        password_hash=hash_password("rahbar123"),
        parent_id=admin.id,
        agent_token=generate_agent_token(),
        is_active=True,
    )
    xodim = User(
        username="xodim",
        full_name="Bo'lim xodimi",
        role="xodim",
        password_hash=hash_password("xodim123"),
        parent_id=rahbar.id,
        agent_token=generate_agent_token(),
        is_active=True,
    )
    db.add_all([rahbar, xodim])
    db.commit()
    db.refresh(rahbar)
    db.refresh(xodim)

    devices = [
        Device(
            serial_number="E0D55E6C382BE820D9430146",
            vendor="KINGSTON",
            model="DATATRAVELER_3.0",
            grif="Nomaxfiy",
            device_type="Fleshka",
            owner_id=rahbar.id,
        ),
        Device(
            serial_number="AA04012700012345",
            vendor="SAMSUNG",
            model="BAR_PLUS",
            grif="Maxfiy",
            device_type="Fleshka",
            owner_id=xodim.id,
        ),
        Device(
            serial_number="WD-WCC4N1234567",
            vendor="WESTERN DIGITAL",
            model="MY_PASSPORT",
            grif="XDFU",
            device_type="Hard disk",
            owner_id=xodim.id,
        ),
    ]
    db.add_all(devices)

    db.add(
        BlacklistEntry(
            serial_number="UNKNOWN-0001",
            vendor="GENERIC",
            model="USB_DISK",
            grif="Noma'lum",
            device_type="Fleshka",
            reason="Ro'yxatda bo'lmagan qurilma aniqlandi",
            status="yangi",
            agent_name="DEMO-PC",
            owner_id=xodim.id,
            event_count=3,
        )
    )
    db.commit()
    print("[seed] Demo ierarxiya yaratildi:")
    print("       rahbar / rahbar123 -> xodim / xodim123")


def main() -> None:
    parser = argparse.ArgumentParser(description="USB Qalqon boshlang'ich ma'lumotlari")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Demo foydalanuvchilar, qurilmalar va qora ro'yxat yozuvlarini qo'shish",
    )
    args = parser.parse_args()

    init_db()
    with SessionLocal() as db:
        ensure_admin(db)
        if args.demo:
            seed_demo(db)


if __name__ == "__main__":
    main()
