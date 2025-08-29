from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Tuple
from util_functions.handle_otp_jwt import get_loggedin_user
from util_functions.for_dashboard import *
from src.integrations.openai import *
from src.config.db import get_supabase   # async supabase factory

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get('/dashboard', response_class=HTMLResponse) #
async def dashboard(request: Request): 
    user, new_access = await get_loggedin_user(request)
    print(user)
    if not user:
        return RedirectResponse("/login")
    
    # ADD THE BUSINESS LOGIC
    supclient = await get_supabase()   # ✅ Supabase client

    # IST ranges
    today_start, today_end = epoch_range_ist(0, 1)
    week_start, week_end = epoch_range_ist(6, 7)
    month_start, month_end = epoch_range_ist(29, 30)

    # fetch rows
    today_rows_raw = await fetch_expenses(supclient, user["id"], today_start, today_end)
    week_rows_raw = await fetch_expenses(supclient, user["id"], week_start, week_end)
    month_rows_raw = await fetch_expenses(supclient, user["id"], month_start, month_end)

    # format today’s rows
    today_rows = [
        {
            "time": epoch_to_ist_time_str(r.get("timestamp")),
            "item": r.get("item_name", ""),
            "amount": int(r.get("amount", 0) or 0),
        }
        for r in today_rows_raw
    ]

    # ---- Numeric summaries ----
    week_total = sum(int(r.get("amount", 0) or 0) for r in week_rows_raw)
    week_txn = len(week_rows_raw)
    month_total = sum(int(r.get("amount", 0) or 0) for r in month_rows_raw)
    month_txn = len(month_rows_raw)

    # ---- GPT category breakdowns ----
    # week_cat = await gpt_category_totals(week_rows_raw)     # List[Tuple[str,int]]
    # month_cat = await gpt_category_totals(month_rows_raw)
    # week_cat_md = make_markdown_table(week_cat)                        # Markdown string
    # month_cat_md = make_markdown_table(month_cat)

    # ---- Render ----
    response = templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "today_rows": today_rows,

        "week_total": week_total,
        "week_avg": round(week_total/7) if week_txn else 0,
        "week_txn": week_txn,
        # "week_cat": week_cat,            # structured list for your current Jinja loop
        # "week_cat_md": week_cat_md,      # optional markdown table string

        "month_total": month_total,
        "month_avg": round(month_total/30) if month_txn else 0,
        "month_txn": month_txn,
        # "month_cat": month_cat,
        # "month_cat_md": month_cat_md,
    }) 
    # Attach cookie to the actual response:
    if new_access:
        response.set_cookie("access_token", new_access, httponly=True, samesite="lax", max_age=3600)
    return response


