from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ============================== Foydalanuvchilar ==============================


class UserBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str


class UserOut(UserBrief):
    role: str
    parent_id: int | None = None
    is_active: bool = True
    is_superuser: bool = False
    created_at: datetime


class UserListItem(UserOut):
    children_count: int = 0
    device_count: int = 0
    blacklist_count: int = 0


class UserTree(UserOut):
    children: list["UserTree"] = Field(default_factory=list)
    device_count: int = 0
    blacklist_count: int = 0


UserTree.model_rebuild()


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")
    full_name: str = Field(default="", max_length=160)
    password: str = Field(min_length=4, max_length=128)
    role: str = Field(default="xodim", max_length=32)
    parent_id: int | None = None
    is_active: bool = True
    is_superuser: bool = False


class UserUpdate(BaseModel):
    username: str | None = Field(
        default=None, min_length=3, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$"
    )
    full_name: str | None = Field(default=None, max_length=160)
    password: str | None = Field(default=None, min_length=4, max_length=128)
    role: str | None = Field(default=None, max_length=32)
    parent_id: int | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None


# ============================== Qurilmalar ==============================


class DeviceBase(BaseModel):
    serial_number: str = Field(min_length=1, max_length=255)
    vendor: str = Field(default="", max_length=160)
    model: str = Field(default="", max_length=200)
    grif: str = Field(default="Nomaxfiy", max_length=64)
    device_type: str = Field(default="USB qurilma", max_length=80)


class DeviceCreate(DeviceBase):
    owner_id: int | None = None


class DeviceUpdate(BaseModel):
    serial_number: str | None = Field(default=None, min_length=1, max_length=255)
    vendor: str | None = Field(default=None, max_length=160)
    model: str | None = Field(default=None, max_length=200)
    grif: str | None = Field(default=None, max_length=64)
    device_type: str | None = Field(default=None, max_length=80)
    owner_id: int | None = None


class DeviceOut(DeviceBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    owner: UserBrief | None = None
    created_at: datetime
    updated_at: datetime


class DevicePage(BaseModel):
    items: list[DeviceOut]
    total: int
    page: int
    page_size: int


class ImportResult(BaseModel):
    filename: str
    total_records: int
    imported: int
    skipped: int
    errors: list[str] = Field(default_factory=list)


# ============================== Qora ro'yxat ==============================


class BlacklistBase(BaseModel):
    serial_number: str = Field(min_length=1, max_length=255)
    vendor: str = Field(default="", max_length=160)
    model: str = Field(default="", max_length=200)
    grif: str = Field(default="", max_length=64)
    device_type: str = Field(default="USB qurilma", max_length=80)
    reason: str = Field(default="", max_length=2000)
    status: Literal["yangi", "korildi", "bloklandi"] = "yangi"
    agent_name: str = Field(default="", max_length=160)


class BlacklistCreate(BlacklistBase):
    owner_id: int | None = None


class BlacklistOut(BlacklistBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    owner: UserBrief | None = None
    event_count: int
    first_seen_at: datetime
    last_seen_at: datetime
    created_at: datetime
    updated_at: datetime


class BlacklistPage(BaseModel):
    items: list[BlacklistOut]
    total: int
    page: int
    page_size: int


# ============================== Agent API ==============================


class AgentLoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class AgentLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    agent_token: str
    username: str
    full_name: str
    role: str
    is_superuser: bool = False
    server_time: datetime


class AgentReport(BaseModel):
    serial_number: str = Field(min_length=1, max_length=255)
    vendor: str = Field(default="", max_length=160)
    model: str = Field(default="", max_length=200)
    grif: str = Field(default="", max_length=64)
    device_type: str = Field(default="USB qurilma", max_length=80)
    reason: str = Field(default="", max_length=2000)
    agent_name: str = Field(default="", max_length=160)


class AgentReportResult(BaseModel):
    created: bool
    entry: BlacklistOut


class AgentCheckResult(BaseModel):
    serial_number: str
    allowed: bool
    registered: bool
    grif: str = ""
    owner_username: str = ""
    owner_full_name: str = ""


class AgentHeartbeat(BaseModel):
    ok: bool
    username: str
    full_name: str
    server_time: datetime


class AgentDevice(BaseModel):
    serial_number: str
    vendor: str = ""
    model: str = ""
    grif: str = ""
    device_type: str = "USB qurilma"
    owner_username: str = ""
    owner_full_name: str = ""


class AgentDeviceCreate(BaseModel):
    serial_number: str = Field(min_length=1, max_length=255)
    vendor: str = Field(default="", max_length=160)
    model: str = Field(default="", max_length=200)
    grif: str = Field(default="Nomaxfiy", max_length=64)
    device_type: str = Field(default="USB qurilma", max_length=80)


class AgentDeviceUpdate(BaseModel):
    vendor: str | None = Field(default=None, max_length=160)
    model: str | None = Field(default=None, max_length=200)
    grif: str | None = Field(default=None, max_length=64)
    device_type: str | None = Field(default=None, max_length=80)


# ============================== Bildirishnomalar ==============================


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    message: str
    kind: str
    blacklist_entry_id: int | None = None
    is_read: bool
    created_at: datetime


class NotificationPage(BaseModel):
    items: list[NotificationOut]
    total: int
    unread: int
    page: int
    page_size: int


class NotificationCount(BaseModel):
    unread: int


# ============================== Auth / Stats / Software ==============================


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    agent_token: str = ""
    user: UserOut


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=4, max_length=128)


class StatsOut(BaseModel):
    total_devices: int
    total_blacklist: int
    total_users: int
    new_blacklist: int
    grif_breakdown: dict[str, int]
    recent_blacklist: list[BlacklistOut]


class AgentPackageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    version: str
    size: int
    sha256: str
    uploaded_at: datetime
    download_url: str


class SoftwareInfo(BaseModel):
    username: str
    full_name: str
    server_url: str
    docs_url: str
    agent_token: str
    poll_seconds: int = 10
    is_superuser: bool = False
    package: AgentPackageOut | None = None
