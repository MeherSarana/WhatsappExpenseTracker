import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src.integrations.twilio_works import send_daily_summary
from src.config.db import get_supabase
from fastapi import APIRouter

scheduler = AsyncIOScheduler()
# router = APIRouter()

async def schedule_user_jobs(mobile: str, cron_time: str):
    """(Re)schedule a single user's summary job."""
    try:
        hour, minute, *_ = map(int, cron_time.split(":"))
    except Exception:
        hour, minute = 21, 0  # default fallback

    async def job(m=mobile):
        await send_daily_summary()

    job_id = f"daily_summary_{mobile}"

    # Remove old job if exists
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    scheduler.add_job(
        job,
        "cron",
        hour=hour,
        minute=minute,
        id=job_id,
        replace_existing=True
    )
    print(f"📅 Scheduled summary for {mobile} at {hour:02d}:{minute:02d}")

async def schedule_all_users():
    """Load all users from DB and schedule their jobs."""
    supclient = await get_supabase()
    users = await supclient.table("users").select("mobile_number, cron_time").execute()

    for u in users.data:
        mobile = u.get("mobile_number")
        cron_time = u.get("cron_time") or "18:00"
        await schedule_user_jobs(mobile, cron_time)

async def init_scheduler():
    """Start scheduler and load all jobs."""
    if not scheduler.running:
        await schedule_all_users()
        scheduler.start()
        print("🚀 APScheduler started")

# from apscheduler.schedulers.asyncio import AsyncIOScheduler
# from src.integrations.twilio_works import send_daily_summary

# For testing asyncioscheduler:
# async def printhello():
#     print("Hellotesting...") ##  to test uncomment the 13th line

# # Background scheduler
# scheduler = AsyncIOScheduler()
# # Run every day at 21:00 (9 PM) → adjust time as you like
# # scheduler.add_job(lambda: asyncio.run(send_daily_summary()), "cron", hour=12, minute=36) #previous version
# scheduler.add_job((send_daily_summary), "cron", hour=13, minute=42) # pass function, not call
# # scheduler.add_job((printhello), "interval", seconds=5)
# scheduler.start()
