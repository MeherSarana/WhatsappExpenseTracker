from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Tuple
from util_functions.handle_otp_jwt import get_loggedin_user
from src.integrations.openai import *
from src.config.db import get_supabase



IST = timezone(timedelta(hours=5, minutes=30))

def get_current_user_id(_: Request) -> str:
    return "demo-user-id"   # later replace with session/mobile

def epoch_to_ist_time_str(epoch_val: int | float) -> str:
    ts = float(epoch_val)
    if ts > 1_000_000_000_000:  # ms
        ts = ts / 1000.0
    dt = datetime.fromtimestamp(ts, tz=IST)
    return dt.strftime("%I:%M %p")

def epoch_range_ist(days_back: int, days_len: int = 1) -> Tuple[int, int]:
    now_ist = datetime.now(IST)
    start_ist = (now_ist - timedelta(days=days_back)).replace(hour=0, minute=0, second=0, microsecond=0)
    end_ist = start_ist + timedelta(days=days_len)
    return int(start_ist.timestamp()), int(end_ist.timestamp())

async def fetch_expenses(supclient, user: int, start_epoch: int, end_epoch: int):
    
        mobile_number = await supclient.table("users").select("mobile_number").eq("id",user).execute()
        mob_= mobile_number.data[0]["mobile_number"]
        res = await (
            supclient.table("expenses_record")
            .select("*")
            .eq("mobile_number", mob_)   # ✅ path parameter is used here
            .gte("timestamp", start_epoch)
            .lt("timestamp", end_epoch)
            .execute()
        )
        print(res.data)
        return res.data or []
