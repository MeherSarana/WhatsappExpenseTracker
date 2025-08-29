from fastapi import APIRouter, HTTPException, Request, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, JSONResponse
from src.config.db import get_supabase, check_if_user_exists
from util_functions.handle_otp_jwt import generate_otp, create_jwt_token
from import_env import *
from src.integrations.twilio_works import send_whatsapp_message
import time
import pyotp

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get('/')
def root():
    return RedirectResponse('/home')

@router.get('/home')
def home(request: Request):
    return templates.TemplateResponse("home.html", { 'request': request})

@router.post('/home')
def home(request: Request,mobile = Form(...)):
    response = RedirectResponse("/login", status_code=303)
    response.set_cookie("pending_mobile",mobile, httponly=True, max_age=300)
    return response
    # return templates.TemplateResponse("home.html", { 'request': request})

@router.get('/about')
def about(request: Request):
    return templates.TemplateResponse("about.html", { 'request': request})

@router.get('/guidelines')
def guidelines(request: Request):
    return templates.TemplateResponse("guidelines.html", { 'request': request})

@router.get('/signup')
def signup(request: Request):
    return templates.TemplateResponse("signup.html", { 'request': request})

@router.get('/login')
def login(request: Request):
    mobile = request.cookies.get('pending_mobile')
    return templates.TemplateResponse('login.html',{'request':request, 'mobile':mobile})
    # return templates.TemplateResponse("login.html", {
    #     'request': request
    # })

@router.post('/api/login')
async def api_login(request: Request, mobile=Form(...)):

    wh_number=f"+91{mobile}"
    supclient = await get_supabase()
    result1 = await supclient.table("users").select("*").eq('mobile_number',wh_number).execute()
    
    if result1.data:
        TOTP_secret=result1.data[0]['totp_secret']
        otp = generate_otp(TOTP_secret)
        twil_num = os.getenv("twilio_number")
        await send_whatsapp_message(
            from_=f"whatsapp:{twil_num}",
            to=f"whatsapp:{wh_number}",
            body=otp
        )

        response = RedirectResponse("/api/otp-login", status_code=303)
        response.set_cookie("pending_mobile",mobile, httponly=True, max_age=300)
        return response

@router.get('/api/otp-login')
async def api_otp_login(request: Request):
    mobile = request.cookies.get('pending_mobile')
    return templates.TemplateResponse('login2.html',{'request':request, 'mobile':mobile})

@router.post('/api/otp-login')
async def api_otp_login(request: Request, mobile=Form(...), d1: str=Form(...),d2: str=Form(...),d3: str=Form(...),d4: str=Form(...),d5: str=Form(...),d6: str=Form(...)):
    otp = d1+d2+d3+d4+d5+d6
    wh_number=f"+91{mobile}"
    supclient = await get_supabase()
    result1 = await supclient.table("users").select("*").eq('mobile_number',wh_number).execute()
    
    if result1.data:
        TOTP_secret=result1.data[0]['totp_secret']
        totp = pyotp.TOTP(TOTP_secret, interval=30)
        # Calculate current counter (time window)
        current_counter = int(time.time()) // 30

        user_record = await supclient.table("users").select("*").eq('mobile_number',wh_number).execute()
        last_used_window = user_record.data[0]["otp_last_used_counter"]

        if last_used_window is not None and last_used_window == current_counter:
            raise HTTPException(status_code=403, detail="OTP already used")
        # Verify OTP correctness:
        if not totp.verify(otp, valid_window=1):
            raise HTTPException(status_code=401, detail="Invalid or expired OTP")
        
        await supclient.table("users").update({'otp_last_used_counter':current_counter}).eq('mobile_number',wh_number).execute()

        user_supa_id = user_record.data[0]["id"]

        access_token, refresh_token = create_jwt_token(str(user_supa_id))

        response = RedirectResponse(url="/dashboard", status_code=302)
        response.set_cookie(
            "access_token", access_token,
            httponly=True, 
            # secure=True, 
            samesite='lax', 
            max_age=3600
        )
        response.set_cookie(
            "refresh_token",refresh_token, 
            httponly=True, 
            # secure=True, 
            samesite='lax', 
            max_age=604800
        )
        response.delete_cookie("pending_mobile")
        return response
    
@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/home", status_code=303)
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return response



