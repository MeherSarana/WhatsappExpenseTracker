from fastapi import APIRouter
from src.services.cronjob import init_scheduler

router = APIRouter()

@router.on_event("startup")
async def start_cron_jobs():
    await init_scheduler()
