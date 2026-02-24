"""Snapshot CRUD endpoints."""

import json
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..schemas import SnapshotCreate, SnapshotResponse
from ...db.database import get_db
from ...db.models import Snapshot
from ...engine.orchestrator import run_calculations

router = APIRouter(prefix="/api/snapshots", tags=["snapshots"])


@router.post("", response_model=SnapshotResponse)
def create_snapshot(request: SnapshotCreate, db: Session = Depends(get_db)):
    engine_inputs = request.inputs.to_engine_inputs()

    if request.results:
        results_data = request.results
    else:
        results_data = run_calculations(engine_inputs)

    snapshot = Snapshot(
        notes=request.notes,
        inputs_json=json.dumps(engine_inputs, default=str),
        results_json=json.dumps(results_data, default=str),
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)

    return SnapshotResponse(
        id=snapshot.id,
        timestamp=snapshot.timestamp,
        notes=snapshot.notes,
        inputs=snapshot.inputs,
        results=snapshot.results,
    )


@router.get("", response_model=List[SnapshotResponse])
def list_snapshots(
    mill_id: str = "pine_hill",
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    snapshots = (
        db.query(Snapshot)
        .filter(Snapshot.mill_id == mill_id)
        .order_by(Snapshot.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [
        SnapshotResponse(
            id=s.id, timestamp=s.timestamp, notes=s.notes,
            inputs=s.inputs, results=s.results,
        ) for s in snapshots
    ]


@router.get("/{snapshot_id}", response_model=SnapshotResponse)
def get_snapshot(snapshot_id: int, db: Session = Depends(get_db)):
    snapshot = db.query(Snapshot).filter(Snapshot.id == snapshot_id).first()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return SnapshotResponse(
        id=snapshot.id, timestamp=snapshot.timestamp, notes=snapshot.notes,
        inputs=snapshot.inputs, results=snapshot.results,
    )


@router.delete("/{snapshot_id}")
def delete_snapshot(snapshot_id: int, db: Session = Depends(get_db)):
    snapshot = db.query(Snapshot).filter(Snapshot.id == snapshot_id).first()
    if not snapshot:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    db.delete(snapshot)
    db.commit()
    return {"status": "deleted"}
