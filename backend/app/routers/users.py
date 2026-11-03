from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..deps import get_current_user
from ..hierarchy import (
    descendant_ids,
    ensure_can_assign_parent,
    ensure_no_cycle,
    ensure_visible,
    get_user_or_404,
    is_admin,
)
from ..models import BlacklistEntry, Device, User
from ..schemas import UserCreate, UserListItem, UserOut, UserTree, UserUpdate
from ..security import generate_agent_token, hash_password

router = APIRouter(prefix="/api/users", tags=["Foydalanuvchilar"])


def _list_item(user: User) -> UserListItem:
    return UserListItem(
        **UserOut.model_validate(user).model_dump(),
        children_count=len(user.children),
        device_count=len(user.devices),
        blacklist_count=len(user.blacklist_entries),
    )


def _base_query(db: Session, current: User):
    ids = descendant_ids(db, current)
    return (
        db.query(User)
        .options(
            selectinload(User.children),
            selectinload(User.devices),
            selectinload(User.blacklist_entries),
        )
        .filter(User.id.in_(ids))
    )


@router.get(
    "",
    response_model=list[UserListItem],
    summary="Ko'rinadigan foydalanuvchilar ro'yxati",
)
def list_users(
    search: str | None = Query(default=None, description="login, F.I.Sh yoki rol bo'yicha"),
    include_inactive: bool = Query(default=True),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    query = _base_query(db, current)
    if not include_inactive:
        query = query.filter(User.is_active.is_(True))
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                User.username.ilike(pattern),
                User.full_name.ilike(pattern),
                User.role.ilike(pattern),
            )
        )
    users = query.order_by(User.id.asc()).all()
    return [_list_item(user) for user in users]


@router.get(
    "/tree",
    response_model=list[UserTree],
    summary="Foydalanuvchilar ierarxiyasi",
)
def users_tree(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    ids = descendant_ids(db, current)
    users = (
        db.query(User)
        .options(
            selectinload(User.devices),
            selectinload(User.blacklist_entries),
        )
        .filter(User.id.in_(ids))
        .order_by(User.id.asc())
        .all()
    )

    nodes: dict[int, UserTree] = {}
    for user in users:
        nodes[user.id] = UserTree(
            **UserOut.model_validate(user).model_dump(),
            device_count=len(user.devices),
            blacklist_count=len(user.blacklist_entries),
        )

    roots: list[UserTree] = []
    for user in users:
        node = nodes[user.id]
        if user.parent_id and user.parent_id in nodes:
            nodes[user.parent_id].children.append(node)
        else:
            roots.append(node)

    return roots


@router.get("/{user_id}", response_model=UserListItem, summary="Bitta foydalanuvchi")
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    target = get_user_or_404(db, user_id)
    ensure_visible(db, current, target)
    return _list_item(target)


@router.post(
    "",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    summary="Yangi foydalanuvchi (bola) qo'shish",
)
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu login allaqachon band",
        )

    # parent_id umuman yuborilmasa — yangi foydalanuvchi joriy foydalanuvchining
    # bolasi bo'ladi. Administrator aniq `null` yuborsa, ildiz foydalanuvchi yaratadi.
    if "parent_id" in payload.model_fields_set:
        parent_id = payload.parent_id
    else:
        parent_id = current.id

    ensure_can_assign_parent(db, current, parent_id)

    user = User(
        username=payload.username,
        full_name=payload.full_name,
        role=payload.role,
        password_hash=hash_password(payload.password),
        parent_id=parent_id,
        agent_token=generate_agent_token(),
        is_active=payload.is_active,
        is_superuser=bool(payload.is_superuser and is_admin(current)),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/{user_id}", response_model=UserOut, summary="Foydalanuvchini tahrirlash")
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    target = get_user_or_404(db, user_id)
    ensure_visible(db, current, target)

    data = payload.model_dump(exclude_unset=True)

    if "username" in data and data["username"] != target.username:
        if db.query(User).filter(User.username == data["username"]).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bu login allaqachon band",
            )

    if "parent_id" in data:
        ensure_no_cycle(db, target, data["parent_id"])
        ensure_can_assign_parent(db, current, data["parent_id"])

    if "is_superuser" in data:
        if not is_admin(current):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Administrator huquqini faqat administrator beradi",
            )
        if target.id == current.id and data["is_superuser"] is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="O'zingizdan administrator huquqini olib tashlay olmaysiz",
            )

    if "password" in data:
        target.password_hash = hash_password(data.pop("password"))

    for field, value in data.items():
        setattr(target, field, value)

    db.add(target)
    db.commit()
    db.refresh(target)
    return target


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Foydalanuvchini (va uning bo'limini) o'chirish",
)
def delete_user(
    user_id: int,
    force: bool = Query(
        default=False,
        description="true bo'lsa bolalari va qurilmalari bilan birga o'chiriladi",
    ),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    target = get_user_or_404(db, user_id)
    ensure_visible(db, current, target)

    if target.id == current.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="O'zingizni o'chira olmaysiz",
        )

    ids_to_delete = descendant_ids(db, target)

    if not force:
        has_children = (
            db.query(User).filter(User.parent_id == target.id).count() > 0
        )
        has_devices = (
            db.query(Device).filter(Device.owner_id == target.id).count() > 0
        )
        has_blacklist = (
            db.query(BlacklistEntry)
            .filter(BlacklistEntry.owner_id == target.id)
            .count()
            > 0
        )
        if has_children or has_devices or has_blacklist:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Foydalanuvchining bolalari yoki ma'lumotlari mavjud. "
                    "force=true bilan birga o'chirish mumkin."
                ),
            )

    # Avlodlarning ma'lumotlarini avval o'chiramiz, keyin foydalanuvchilarni.
    db.query(Device).filter(Device.owner_id.in_(ids_to_delete)).delete(
        synchronize_session=False
    )
    db.query(BlacklistEntry).filter(
        BlacklistEntry.owner_id.in_(ids_to_delete)
    ).delete(synchronize_session=False)
    db.query(User).filter(User.id.in_(ids_to_delete)).delete(
        synchronize_session=False
    )
    db.commit()
    return None
