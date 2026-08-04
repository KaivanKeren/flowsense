from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from ..schemas import AlertCreate, AlertResponse
from ...database.database import get_db
from ...database.models import Alert

router = APIRouter()

@router.post("/", response_model=AlertResponse)
async def create_alert(alert: AlertCreate, db: AsyncSession = Depends(get_db)):
    db_item = Alert(**alert.model_dump())
    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)
    return db_item

@router.get("/", response_model=List[AlertResponse])
async def get_alerts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Alert))
    return result.scalars().all()
