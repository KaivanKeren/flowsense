from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Annotated, List
from ..schemas import IntersectionCreate, IntersectionResponse
from ...database.database import get_db
from ...database.models import Intersection

router = APIRouter()

@router.post("/", response_model=IntersectionResponse)
async def create_intersection(intersection: IntersectionCreate, db: Annotated[AsyncSession, Depends(get_db)]):
    db_item = Intersection(**intersection.model_dump())
    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)
    return db_item

@router.get("/", response_model=List[IntersectionResponse])
async def get_intersections(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(Intersection))
    return result.scalars().all()
