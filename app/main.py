import logging
import os
from contextlib import asynccontextmanager
from typing import Dict

from dotenv import load_dotenv
from fastapi import FastAPI

from app.db import init_db, list_events
from app.webhooks.provider import router as provider_router

# Load .env if present (safe no-op if missing)
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Initialize SQLite database on startup.
    """
    db_path = os.getenv("DATABASE_PATH", "./data/app.db")
    init_db(db_path)
    logger.info({"event": "startup", "db_path": db_path})
    yield


app = FastAPI(title="Fintech Integration Lab", lifespan=lifespan)
app.include_router(provider_router)


@app.get("/health")
def health_check() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/events")
def get_events():
    return {"events": list_events()}
