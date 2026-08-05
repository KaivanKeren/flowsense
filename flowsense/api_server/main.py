from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

load_dotenv()

from .routes import router
from ..database.database import engine, Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB
    yield
    await engine.dispose()

app = FastAPI(title="FlowSense API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")
