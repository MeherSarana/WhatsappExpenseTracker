import pyotp
import jwt 
from datetime import datetime, timedelta, timezone
from import_env import *
from fastapi import Request
from src.config.db import get_supabase

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

def generate_otp(TOTP_SECRET):
    totp = pyotp.TOTP(TOTP_SECRET, interval=30)  
    otp = totp.now()
    return otp

def create_jwt_token(user_id: str):

    now = datetime.now(timezone.utc)

    # Access token (short expiry)
    access_exp = now + timedelta(minutes=30)
    access_payload = {"sub": user_id, "exp": access_exp}
    access_token = jwt.encode(access_payload, SECRET_KEY, algorithm=ALGORITHM)
    if isinstance(access_token, bytes):  # ensure string
        access_token = access_token.decode("utf-8")

    # Refresh token (longer expiry)
    refresh_exp = now + timedelta(days=7)
    refresh_payload = {"sub": user_id, "exp": refresh_exp, "type": "refresh"}
    refresh_token = jwt.encode(refresh_payload, SECRET_KEY, algorithm=ALGORITHM)
    if isinstance(refresh_token, bytes):  # ensure string
        refresh_token = refresh_token.decode("utf-8")

    return access_token, refresh_token

async def get_loggedin_user(request: Request): 
    access_token = request.cookies.get("access_token")
    refresh_token = request.cookies.get("refresh_token")
    print("DEBUG: hello access token =", access_token)
    print("DEBUG: hello refresh token =", refresh_token)
    if not access_token and not refresh_token:
        return None, None
    try:
        # try normal access token first
        payload = jwt.decode(
            access_token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"require":['sub','exp']}
        )
        print("DEBUG: decoded access payload =", payload)
        user_id = payload.get("sub")
        if user_id is None:
            return None, None
        else:
            #  Fetch user from database using the user_id
            supclient = await get_supabase()
            record = await supclient.table("users").select("*").eq("id", int(user_id)).single().execute()
            if not record or not record.data:
                return None, None
            else:
                return record.data, None  # the full user record (dict)

    except jwt.ExpiredSignatureError:
        # access token expired then try refresh token:
        try:
            payload = jwt.decode(
                refresh_token,
                SECRET_KEY,
                algorithms=[ALGORITHM],
                options={"require":['sub','exp','type']}
            )
            print("DEBUG: decoded refresh payload =", payload)

            if payload.get("type") != "refresh":
                raise jwt.InvalidTokenError("Not a refresh token")
            
            user_id = payload.get("sub")
            if user_id is None:
                return None, None
            
            new_access, _ = create_jwt_token(str(user_id))

            #  Fetch user from database using the user_id
            supclient = await get_supabase()
            record = await supclient.table("users").select("*").eq("id", int(user_id)).single().execute()
            if not record or not record.data:
                return None, None
            else:
                return record.data, new_access  # the full user record (dict)
        
        except jwt.ExpiredSignatureError:
            print("DEBUG: token expired")
            # Token expired
            return None, None
        except jwt.InvalidTokenError as e:
            print("DEBUG: token invalid:", e)
            # Token invalid or tampered
            return None, None
        except Exception as e:
            print("DEBUG: unexpected error in get_loggedin_user:", str(e))
            return None, None
    except jwt.InvalidTokenError as e:
        print("DEBUG: token invalid:", e)
        # Token invalid or tampered
        return None, None
    except Exception as e:
        print("DEBUG: unexpected error in get_loggedin_user:", str(e))
        return None, None
    