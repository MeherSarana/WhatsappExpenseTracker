from import_env import *
from supabase import create_async_client, Client as SupabaseClient

supabase: SupabaseClient = None  # cached client

# For creating/grabing Supabase client
async def get_supabase(): 
    """
    Returns a cached Supabase client if available,
    otherwise creates a new one and reuses it.
    """
    global supabase
    if supabase is None:  # first time only
        supabase_url = os.getenv("supabase_url")
        supabase_key = os.getenv("supabase_key")
        supabase = await create_async_client(supabase_url, supabase_key)
    return supabase

# To check if user already exists in the supabase "users" table
async def check_if_user_exists(supclient, mobile):
    """Check if a user with this mobile already exists in Supabase."""
    # supclient = await get_supabase()
    result = await supclient.table("users").select("*").eq("mobile_number", mobile).execute()
    return len(result.data) > 0

