from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..deps import get_current_user
from ..hierarchy import descendant_ids
from ..models import BlacklistEntry, Device, User
from ..schemas import StatsOut

router = APIRouter(prefix="/api/stats", tags=["Statistika"])


@router.get("", response_model=StatsOut, summary="Bosh sahifa statistikasi")
def stats(
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    ids = descendant_ids(db, current)

    total_devices = (
        db.query(func.count(Device.id))
        .filter(Device.owner_id.in_(ids))
        .scalar()
        or 0
    )
    total_blacklist = (
        db.query(func.count(BlacklistEntry.id))
        .filter(BlacklistEntry.owner_id.in_(ids))
        .scalar()
        or 0
    )
    new_blacklist = (
        db.query(func.count(BlacklistEntry.id))
        .filter(
            BlacklistEntry.owner_id.in_(ids),
            BlacklistEntry.status == "yangi",
        )
        .scalar()
        or 0
    )
    total_users = len(ids)

    breakdown_rows = (
        db.query(Device.grif, func.count(Device.id))
        .filter(Device.owner_id.in_(ids))
        .group_by(Device.grif)
        .all()
    )
    grif_breakdown = {grif or "Noma'lum": count for grif, count in breakdown_rows}

    recent = (
        db.query(BlacklistEntry)
        .options(joinedload(BlacklistEntry.owner))
        .filter(BlacklistEntry.owner_id.in_(ids))
        .order_by(BlacklistEntry.last_seen_at.desc())
        .limit(5)
        .all()
    )

    return StatsOut(
        total_devices=total_devices,
        total_blacklist=total_blacklist,
        total_users=total_users,
        new_blacklist=new_blacklist,
        grif_breakdown=grif_breakdown,
        recent_blacklist=recent,
    )
