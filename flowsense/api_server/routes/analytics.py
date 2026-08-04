from fastapi import APIRouter, Depends
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from ...database.database import get_db

router = APIRouter()

@router.get("/")
async def get_analytics(db: Annotated[AsyncSession, Depends(get_db)]):
    return {"status": "analytics_endpoint_stub"}
