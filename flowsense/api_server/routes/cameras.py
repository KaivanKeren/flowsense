import json
import os
from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from ..schemas import CameraCreate, CameraResponse
from ...database.database import get_db
from ...database.models import Camera

router = APIRouter()
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    expected_api_key = os.getenv("FLOWSENSE_API_KEY")
    if expected_api_key and api_key_header == expected_api_key:
        return api_key_header
    raise HTTPException(status_code=403, detail="Could not validate API Key")

@router.post("/", response_model=CameraResponse)
async def create_camera(camera: CameraCreate, db: AsyncSession = Depends(get_db)):
    db_camera = Camera(**camera.model_dump())
    db.add(db_camera)
    await db.commit()
    await db.refresh(db_camera)
    return db_camera

@router.get("/", response_model=List[CameraResponse])
async def get_cameras(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Camera))
    return result.scalars().all()

@router.get("/posko")
async def get_posko_cameras(api_key: str = Depends(get_api_key)):
    try:
        with open("data/posko_cctv.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Posko CCTV data not found")

@router.get("/kudus")
async def get_kudus_cameras(api_key: str = Depends(get_api_key)):
    try:
        with open("data/kudus_cctv.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Kudus CCTV data not found")
