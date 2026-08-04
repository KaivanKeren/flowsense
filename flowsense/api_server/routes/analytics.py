from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ...database.database import get_db

router = APIRouter()

@router.get("/")
async def get_analytics(db: AsyncSession = Depends(get_db)):
    return {"status": "analytics_endpoint_stub"}
