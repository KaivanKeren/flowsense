from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Annotated, List, Optional
from datetime import datetime
from ..schemas import DetectionCreate, DetectionResponse
from ...database.database import get_db
from ...database.models import Detection

router = APIRouter()

@router.post("/", response_model=DetectionResponse)
async def create_detection(detection: DetectionCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    db_det = Detection(**detection.model_dump())
    db.add(db_det)
    await db.commit()
    await db.refresh(db_det)
    return db_det

@router.get("/", response_model=List[DetectionResponse])
async def get_detections(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    query = select(Detection)
    if start_time:
        query = query.where(Detection.timestamp >= start_time)
    if end_time:
        query = query.where(Detection.timestamp <= end_time)
    result = await db.execute(query)
    return result.scalars().all()
