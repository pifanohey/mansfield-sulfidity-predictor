"""Trend point CRUD endpoints for sulfidity model-vs-lab tracking."""

from datetime import datetime, timedelta, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..schemas import TrendPointCreate, TrendPointUpdate, TrendPointResponse
from ...db.database import get_db
from ...db.models import TrendPoint

router = APIRouter(prefix="/api/trends", tags=["trends"])


@router.post("", response_model=TrendPointResponse)
def create_trend(data: TrendPointCreate, db: Session = Depends(get_db)):
    point = TrendPoint(
        predicted_sulfidity_pct=data.predicted_sulfidity_pct,
        smelt_sulfidity_pct=data.smelt_sulfidity_pct,
        nash_dry_lb_hr=data.nash_dry_lb_hr,
        naoh_dry_lb_hr=data.naoh_dry_lb_hr,
        target_sulfidity_pct=data.target_sulfidity_pct,
    )
    db.add(point)
    db.commit()
    db.refresh(point)
    return TrendPointResponse(
        id=point.id,
        mill_id=point.mill_id,
        timestamp=point.timestamp,
        predicted_sulfidity_pct=point.predicted_sulfidity_pct,
        smelt_sulfidity_pct=point.smelt_sulfidity_pct,
        nash_dry_lb_hr=point.nash_dry_lb_hr,
        naoh_dry_lb_hr=point.naoh_dry_lb_hr,
        target_sulfidity_pct=point.target_sulfidity_pct,
        lab_sulfidity_pct=point.lab_sulfidity_pct,
        notes=point.notes or "",
    )


@router.get("", response_model=List[TrendPointResponse])
def list_trends(
    hours: int = Query(default=168, ge=1, le=8760),
    mill_id: str = "pine_hill",
    db: Session = Depends(get_db),
):
    query = db.query(TrendPoint).filter(TrendPoint.mill_id == mill_id)
    if hours > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        query = query.filter(TrendPoint.timestamp >= cutoff)
    points = query.order_by(TrendPoint.timestamp.asc()).all()
    return [
        TrendPointResponse(
            id=p.id,
            mill_id=p.mill_id,
            timestamp=p.timestamp,
            predicted_sulfidity_pct=p.predicted_sulfidity_pct,
            smelt_sulfidity_pct=p.smelt_sulfidity_pct,
            nash_dry_lb_hr=p.nash_dry_lb_hr,
            naoh_dry_lb_hr=p.naoh_dry_lb_hr,
            target_sulfidity_pct=p.target_sulfidity_pct,
            lab_sulfidity_pct=p.lab_sulfidity_pct,
            notes=p.notes or "",
        )
        for p in points
    ]


@router.patch("/{point_id}", response_model=TrendPointResponse)
def update_trend(
    point_id: int,
    update: TrendPointUpdate,
    db: Session = Depends(get_db),
):
    point = db.query(TrendPoint).filter(TrendPoint.id == point_id).first()
    if not point:
        raise HTTPException(status_code=404, detail="Trend point not found")
    if update.lab_sulfidity_pct is not None:
        point.lab_sulfidity_pct = update.lab_sulfidity_pct
    if update.notes is not None:
        point.notes = update.notes
    db.commit()
    db.refresh(point)
    return TrendPointResponse(
        id=point.id,
        mill_id=point.mill_id,
        timestamp=point.timestamp,
        predicted_sulfidity_pct=point.predicted_sulfidity_pct,
        smelt_sulfidity_pct=point.smelt_sulfidity_pct,
        nash_dry_lb_hr=point.nash_dry_lb_hr,
        naoh_dry_lb_hr=point.naoh_dry_lb_hr,
        target_sulfidity_pct=point.target_sulfidity_pct,
        lab_sulfidity_pct=point.lab_sulfidity_pct,
        notes=point.notes or "",
    )


@router.delete("/{point_id}")
def delete_trend(point_id: int, db: Session = Depends(get_db)):
    point = db.query(TrendPoint).filter(TrendPoint.id == point_id).first()
    if not point:
        raise HTTPException(status_code=404, detail="Trend point not found")
    db.delete(point)
    db.commit()
    return {"status": "deleted"}
