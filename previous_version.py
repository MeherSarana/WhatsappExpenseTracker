from fastapi import FastAPI, Form, Request
from fastapi.responses import PlainTextResponse, HTMLResponse
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import concurrent.futures
import os
import time
from supabase import create_async_client, Client as SupabaseClient
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import datetime,asyncio
import textwrap

load_dotenv("keys.env")
executor = concurrent.futures.ThreadPoolExecutor()
account_sid=os.getenv("account_sid")
auth_token=os.getenv("auth_token")
client= Client(account_sid,auth_token)

async def send_whatsapp_message(from_, to, body):
    loop = asyncio.get_running_loop()  # get current event loop
    # run blocking Twilio call in a separate thread
    await loop.run_in_executor(
        executor,
        lambda: client.messages.create(from_=from_, to=to, body=body)
    )

supabase: SupabaseClient = None  # cached client

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

def get_today_epoch_range():
    """Return start and end epoch timestamps for today"""
    now = datetime.datetime.now()
    start_of_day = datetime.datetime(now.year, now.month, now.day, 0, 0, 0)
    end_of_day = datetime.datetime(now.year, now.month, now.day, 23, 59, 59)
    return int(start_of_day.timestamp()), int(end_of_day.timestamp())

async def check_if_user_exists(supclient, mobile):
    """Check if a user with this mobile already exists in Supabase."""
    supclient = await get_supabase()
    result = await supclient.table("users").select("*").eq("mobile_number", mobile).execute()
    return len(result.data) > 0

async def register_user(supabase, mobile):
    data = {"mobile_number": mobile}
    await supabase.table("users").insert(data).execute()

    # Send welcome message
    await send_whatsapp_message(
        from_="whatsapp:+14155238886",   # Twilio sandbox / business number
        to=f"whatsapp:{mobile}",
        body=(
            "🎉 Welcome to the WhatsApp Expense Tracker!\n\n"
            "You can now start adding your expenses.\n"
            "👉 Example: 'Apple 50'\n"
            "👉 At the end of the day, you'll receive your daily summary.\n\n"
            "Type /help to see all available commands."
        )
    )
    return True

def clean_number(raw_number):
    if raw_number.startswith("whatsapp:"):
        return raw_number.replace("whatsapp:","")
    return raw_number

def parse_expense_message_by_line(body):
    # Split the message into lines and strip extra spaces
    lines = body.strip().split('\n')
    result = []
    for line in lines:
        line = line.strip()  # remove leading/trailing spaces
        if not line:  # skip empty lines
            continue
        tokens = line.split()
        amount=None
        len_tokens=len(tokens)
        # now for sample tokens=('apple', '50'), check if last value is a digit, if yes, simply consider it as amount.
        if tokens[len_tokens-1].isdigit():
            amount=tokens.pop(len_tokens-1)
            item=" ".join(tokens)
            result.append((item, int(amount)))
            continue
        words = []
        for token in tokens:
            if token.isdigit():
                amount = int(token)
            else:
                words.append(token)
        # Join all words as a single item
        item = " ".join(words)
        if item and amount is not None:
            result.append((item, amount))
    return result
    # sample:
    # body="""Apple 5 kg 50
    # rice 2 kg 60
    # 80      kiwi
    # chicken 65 65
    # """
    # sample result: [('Apple 5 kg', 50), ('rice 2 kg', 60), ('kiwi', 80), ('chicken 65', 65)]
    # still dosen't handle '120 chicken 65' , it gives ('120 chicken', 65)

def format_expense_message(expense_list):
    col_width = 19
    lines = [f"{'Item-name'.ljust(col_width)}Amount", '-' * (col_width + 6)]
    for item, amt in expense_list:
        wrapped = textwrap.wrap(item, width=col_width)
        # when sample item='word1 word2 word3 word4' then wrapped stores a List-of-Strings like ['word1 word2 word3', 'word4']
        for i, line in enumerate(wrapped):
            if i == 0:
                lines.append(f"{line.ljust(col_width)}{amt}")
            else:
                lines.append(line.ljust(col_width))
    # Join all lines and wrap in triple backticks for WhatsApp monospace
    return "```\n" + "\n".join(lines) + "\n```"
#Sample return value:
# Item-name         Amount
# ------------------------
# apple             50
# led bulb factory  60
# unit              
# kiwi              70

def handle_help():
    return (
        "Hi! Here are the commands you can use:\n"
        "/help — Used to Check Out the Commands \n"
        "/totalexpenseoftoday — get today’s total and item breakdown\n"
        "/delete_account — delete your account & all expenses (requires confirmation)\n\n"
        "📌 Example of adding expenses:\n"
        "Apple 50\n"
        "50 Banana"
    )

async def handle_total_today(supclient, mobile):
    start, end = get_today_epoch_range()
    supclient = await get_supabase()
    res = await supclient.table("expenses_record") \
        .select("item_name, amount") \
        .eq("mobile_number", mobile) \
        .gte("timestamp", start) \
        .lt("timestamp", end) \
        .execute()

    rows = res.data or []
    if not rows:
        return "No expenses recorded today."
    
    expense_list = [(r["item_name"], r["amount"]) for r in rows]

    total = sum(r["amount"] for r in rows)

    formatted = format_expense_message(expense_list)
    message = "Today's Expenses:\n" + f"\n{formatted}" + "```\n"+f"{'-'*25}\nTotal = {total}"+ "\n```"

    return message

async def handle_delete_account(supclient, cln_number, Body):
    parts = Body.split()  # split message into words
    # Example: ["/delete_account", "confirm"]

    # Check if user added "confirm"
    if len(parts) > 1 and parts[1].lower() == "confirm":
        try:
            # Delete all expense records for this user
            await supclient.table("expenses_record") \
                .delete() \
                .eq("mobile_number", cln_number) \
                .execute()
            
            await supclient.table("users") \
                .delete() \
                .eq("mobile_number", cln_number) \
                .execute()
            
            return "✅ Your account and all expenses have been deleted."
        except Exception as e:
            print("Supabase delete error:", e)
            return "❌ Error while deleting your account. Please try again."
    else:
        # Ask user to confirm
        return (
            "⚠️ This will permanently delete your account and all expenses.\n"
            "If you’re sure, reply:\n\n"
            "/Delete_Account CONFIRM"
        )

app = FastAPI()

@app.get('/', response_class=HTMLResponse)
async def home():
    with open("home.html", "r") as f:
        home_content= f.read()
    return HTMLResponse(content=home_content)

@app.get('/about', response_class=HTMLResponse)
async def about():
    with open("about.html", "r") as f1:
        about_content= f1.read()
    return HTMLResponse(content=about_content)

@app.post("/whatsapp")
# async def whatsapp_webhook(Body: str = Form(...), From: str = Form(...)):
async def whatsapp_webhook(request:Request):

    form_data= await request.form()
    fdata=dict(form_data)

    From= fdata.get("From") # gives: "whatsapp:+91xxxxxxxxxx"
    Body= fdata.get("Body")
    To= fdata.get("To")
    print(f"Message from {From}: {Body}")

    cln_number = clean_number(From)
    resp1 = parse_expense_message_by_line(Body)
    reply1 = None

    # Initialize Supabase client once
    supclient = await get_supabase()

    cln_number = clean_number(From)  # normalize number (remove whatsapp:+91 etc.)

# Check if new user
    if not await check_if_user_exists(supabase, cln_number):
        await register_user(supabase, cln_number)
        print("Welcome message sent! to",cln_number)
    else:
        if Body.startswith("/"):
            cmd = Body.split()[0].lower()
            if cmd == "/help":
                reply1 = handle_help()
            elif cmd == "/totalexpenseoftoday":
                reply1 = await handle_total_today(supclient, cln_number)
            elif cmd == "/delete_account":
                reply1 = await handle_delete_account(supclient, cln_number, Body)
            else:
                reply1 = "Unknown command. Type /help to see available commands."+ "\n" + handle_help()
        else:
            reply1=format_expense_message(resp1)
            try:
                supclient = await get_supabase()
                for item,amt in resp1:
                    await supclient.table("expenses_record").insert({
                        "mobile_number":cln_number,
                        "item_name":item,
                        "amount":amt,
                        "timestamp":int(time.time())
                    }).execute()
            except Exception as e:
                print("Supabase error: ",e)
        print(resp1)
        print(reply1)
        # replying with a formatted response
        try:
            await send_whatsapp_message(
                from_=To,
                to=From,
                body=reply1
            )

        except TwilioRestException as e:
            print("Twilio error: ",e)

    #simple reply to user
    # try:
    #     client.messages.create(
    #         from_=To,
    #         to=From,
    #         body=f"Got your msg: {Body}"
    #     )
    # except TwilioRestException as e:
    #     print("Twilio error: ",e)

    # return PlainTextResponse("OK")

async def send_daily_summary():

    """Fetch today's expenses for all users and send WhatsApp summary"""
    try:
        supclient = await get_supabase()
        start_epoch, end_epoch = get_today_epoch_range()

        # Get all users who have expenses today
        data = await supclient.table("expenses_record") \
            .select("*") \
            .gte("timestamp", start_epoch) \
            .lte("timestamp", end_epoch) \
            .execute()

        rows = data.data
        if not rows:
            print("No expenses recorded today.")
            return

        # Group expenses by mobile_number
        user_expenses = {}
        for r in rows:
            user_expenses.setdefault(r["mobile_number"], []).append(r)

        # Send each user their own summary
        for mobile, items in user_expenses.items():
            total = sum(r["amount"] for r in items)
            # lines = [f"{r['item_name']} - {r['amount']}" for r in items]
            expense_list = [(r["item_name"], r["amount"]) for r in items]
            lines = format_expense_message(expense_list)
            message = "Today's Expenses:\n" + f"\n{lines}" + "```\n"+f"{'-'*25}\nTotal = {total}"+ "\n```"
            print(message)
            # Send via Twilio
            await send_whatsapp_message(
                from_= "whatsapp:+14155238886",
                to=f"whatsapp:{mobile}",   # add prefix back
                body=message
            )
            print(f"✅ Daily summary sent to {mobile}")

    except Exception as e:
        print("Error in daily summary:", e)

# Background scheduler
scheduler = AsyncIOScheduler()
# Run every day at 21:00 (9 PM) → adjust time as you like
scheduler.add_job((send_daily_summary), "cron", hour=17, minute=43)
scheduler.start()
