import asyncio
from typing import Dict

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from backend.crawler.scheduler import CrawlerScheduler

router = APIRouter(prefix="/crawler", tags=["crawler"])

_scheduler: CrawlerScheduler = None
_scheduler_task = None


class SourceConfig(BaseModel):
    name: str
    url: str
    source_type: str = "rss"
    priority: int = 5
    region: str = None


@router.get("/status")
async def crawler_status():
    global _scheduler
    if not _scheduler:
        return {"running": False, "stats": {}}
    return {"running": True, "stats": _scheduler.stats}


@router.post("/start")
async def start_crawlers(background_tasks: BackgroundTasks):
    global _scheduler, _scheduler_task

    if _scheduler:
        raise HTTPException(status_code=409, detail="Crawlers already running")

    _scheduler = CrawlerScheduler()

    async def run():
        await _scheduler.start()

    background_tasks.add_task(run)
    return {"status": "started"}


@router.post("/stop")
async def stop_crawlers():
    global _scheduler
    if not _scheduler:
        raise HTTPException(status_code=409, detail="Crawlers not running")
    await _scheduler.stop()
    _scheduler = None
    return {"status": "stopped"}


@router.put("/interval")
async def set_interval(seconds: int):
    from backend.config import settings
    if seconds < 60:
        raise HTTPException(status_code=400, detail="Minimum interval 60s")
    settings.CRAWL_INTERVAL_SECONDS = seconds
    return {"interval_seconds": seconds}
