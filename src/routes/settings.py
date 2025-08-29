from fastapi import APIRouter, Request, Depends, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Tuple
from util_functions.handle_otp_jwt import get_loggedin_user
from src.integrations.openai import *
from src.config.db import get_supabase   # async supabase factory

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get('/settings')
async def settings(request: Request):
    user, new_access = await get_loggedin_user(request)
    if not user:
        return RedirectResponse("/login")

    supclient = await get_supabase()
    # Fetch the user record fully (already done in get_loggedin_user, but making sure)
    record = await supclient.table("users").select("*").eq("id", user["id"]).single().execute()
    user_data = record.data

    # Format joined time (epoch/ISO → readable date)
    joined_time = None
    if user_data.get("created_at"):   # assuming supabase default timestamp column
        dt = datetime.fromisoformat(user_data["created_at"].replace("Z","+00:00"))
        joined_time = dt.strftime("%B %d, %Y")

    response = templates.TemplateResponse("settings.html", {
        "request": request,
        "mobile": user_data.get("mobile_number", ""),
        "name": user_data.get("name", ""),
        "email": user_data.get("email", ""),
        "joined": joined_time
    })

    if new_access:
        response.set_cookie("access_token", new_access, httponly=True, samesite="lax", max_age=3600)
    return response

@router.post("/delete-account")
async def delete_account(request: Request):
    user, _ = await get_loggedin_user(request)
    if not user:
        return RedirectResponse("/login")

    supclient = await get_supabase()

    # Delete all expenses for this user
    await supclient.table("expenses_record").delete().eq("mobile_number", user["mobile_number"]).execute()
    # Delete the user record itself
    await supclient.table("users").delete().eq("id", user["id"]).execute()

    # Clear cookies and redirect to home
    response = RedirectResponse(url="/home", status_code=303)
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return response

@router.post("/update-profile")
async def update_profile(request: Request, name: str = Form(...), email: str = Form(...)):
    user, _ = await get_loggedin_user(request)
    if not user:
        return RedirectResponse("/login")

    supclient = await get_supabase()

    # Update user record
    await supclient.table("users").update({
        "name": name,
        "email": email
    }).eq("id", user["id"]).execute()

    # Redirect back to settings page
    return RedirectResponse(url="/settings", status_code=303)



