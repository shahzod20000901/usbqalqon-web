from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.utcnow()


class User(Base):
    """Tashkiliy tuzilmadagi foydalanuvchi."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    full_name = Column(String(160), nullable=False, default="")
    role = Column(String(32), nullable=False, default="xodim")
    password_hash = Column(String(256), nullable=False)
    parent_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    agent_token = Column(String(128), unique=True, index=True, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    is_superuser = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    parent = relationship("User", remote_side=[id], back_populates="children")
    children = relationship(
        "User",
        back_populates="parent",
        cascade="all, delete-orphan",
        single_parent=True,
    )
    devices = relationship(
        "Device",
        back_populates="owner",
        cascade="all, delete-orphan",
    )
    blacklist_entries = relationship(
        "BlacklistEntry",
        back_populates="owner",
        cascade="all, delete-orphan",
    )
    notifications = relationship(
        "Notification",
        back_populates="user",
        cascade="all, delete-orphan",
    )


class Device(Base):
    """Foydalanuvchi bo'limiga tegishli ruxsat etilgan qurilma."""

    __tablename__ = "devices"
    __table_args__ = (
        UniqueConstraint("owner_id", "serial_number", name="uq_device_owner_serial"),
    )

    id = Column(Integer, primary_key=True, index=True)
    serial_number = Column(String(255), nullable=False, index=True)
    vendor = Column(String(160), nullable=False, default="")
    model = Column(String(200), nullable=False, default="")
    grif = Column(String(64), nullable=False, default="Nomaxfiy", index=True)
    device_type = Column(String(80), nullable=False, default="USB qurilma")
    owner_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    owner = relationship("User", back_populates="devices")


class BlacklistEntry(Base):
    """Ro'yxatda bo'lmagan (ruxsat etilmagan) qurilma hodisasi."""

    __tablename__ = "blacklist_entries"
    __table_args__ = (
        UniqueConstraint("owner_id", "serial_number", name="uq_blacklist_owner_serial"),
    )

    id = Column(Integer, primary_key=True, index=True)
    serial_number = Column(String(255), nullable=False, index=True)
    vendor = Column(String(160), nullable=False, default="")
    model = Column(String(200), nullable=False, default="")
    grif = Column(String(64), nullable=False, default="")
    device_type = Column(String(80), nullable=False, default="USB qurilma")
    reason = Column(Text, nullable=False, default="")
    status = Column(String(32), nullable=False, default="yangi", index=True)
    agent_name = Column(String(160), nullable=False, default="")
    event_count = Column(Integer, nullable=False, default=1)
    owner_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    first_seen_at = Column(DateTime, nullable=False, default=utcnow)
    last_seen_at = Column(DateTime, nullable=False, default=utcnow)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    owner = relationship("User", back_populates="blacklist_entries")


class AgentPackage(Base):
    """Superadmin tomonidan yuklangan yagona desktop agent (.exe)."""

    __tablename__ = "agent_packages"

    id = Column(Integer, primary_key=True, index=True)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    version = Column(String(64), nullable=False, default="")
    size = Column(Integer, nullable=False, default=0)
    sha256 = Column(String(64), nullable=False, default="")
    uploaded_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    uploaded_at = Column(DateTime, nullable=False, default=utcnow)

    uploaded_by = relationship("User")


class Notification(Base):
    """Administratorlar uchun bildirishnoma."""

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(200), nullable=False, default="")
    message = Column(Text, nullable=False, default="")
    kind = Column(String(32), nullable=False, default="blacklist", index=True)
    blacklist_entry_id = Column(
        Integer,
        ForeignKey("blacklist_entries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_read = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime, nullable=False, default=utcnow, index=True)

    user = relationship("User", back_populates="notifications")
    blacklist_entry = relationship("BlacklistEntry")
