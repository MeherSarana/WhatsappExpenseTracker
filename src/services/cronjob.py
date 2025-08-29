from apscheduler.schedulers.asyncio import AsyncIOScheduler
from src.integrations.twilio_works import send_daily_summary

# For testing asyncioscheduler:
# async def printhello():
#     print("Hellotesting...") ##  to test uncomment the 13th line

# Background scheduler
scheduler = AsyncIOScheduler()
# Run every day at 21:00 (9 PM) → adjust time as you like
# scheduler.add_job(lambda: asyncio.run(send_daily_summary()), "cron", hour=12, minute=36) #previous version
scheduler.add_job((send_daily_summary), "cron", hour=13, minute=42) # pass function, not call
# scheduler.add_job((printhello), "interval", seconds=5)
scheduler.start()