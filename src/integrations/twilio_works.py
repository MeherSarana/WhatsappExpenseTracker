import concurrent.futures
from twilio.rest import Client as TwilioClient
import asyncio
from src.integrations.openai import *
from src.config.db import * # includes: import_env import *
from util_functions.utilities import *

twilio_client: TwilioClient = None

# create a global thread pool executor
executor = concurrent.futures.ThreadPoolExecutor()

# For creating/grabing twilio client
async def get_twilio_client():
    global twilio_client
    if twilio_client is None:
        twilio_account_sid=os.getenv("account_sid")
        twilio_auth_token=os.getenv("auth_token")
        twilio_client= TwilioClient(twilio_account_sid,twilio_auth_token)
        return twilio_client
    return twilio_client

# Used to send whatsapp msg to user
async def send_whatsapp_message(from_, to, body):
    loop = asyncio.get_running_loop()  # get current event loop
    # run blocking Twilio call in a separate thread
    twilclient = await get_twilio_client()
    await loop.run_in_executor(executor, lambda: twilclient.messages.create(from_=from_, to=to, body=body)
    )

# one of whatsapp '/' helper command handler - to return the total expenses upto the point.
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

# one of whatsapp '/' helper command handler - to proceed with account deletion
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
            # Delete user record from 'users' table
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
            "/Delete_Account confirm"
        )

# Used to send total summary - used by APScheduler for cron-job
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


# twilio_works.py

async def catorgize_items(supclient, cln_number):
    """
    Fetch today's expenses for a given user, categorize them using GPT,
    and return a formatted category-wise breakdown message.
    """

    try:
        supclient = await get_supabase()
        start_epoch, end_epoch = get_today_epoch_range()

        # Fetch today's expenses for the given user
        res = await supclient.table("expenses_record") \
            .select("*") \
            .eq("mobile_number", cln_number) \
            .gte("timestamp", start_epoch) \
            .lt("timestamp", end_epoch) \
            .execute()

        rows = res.data or []
        if not rows:
            return "No expenses recorded today to categorize."

        # Get category totals from GPT
        cat_list = await gpt_category_totals(rows)   # List[(category, amount)]

        # Format into a readable message
        message_lines = ["📊 Today's Category Breakdown:"]
        total = 0
        for cat, amt in cat_list:   # <- for-loop
            message_lines.append(f"{cat}: ₹{amt}")
            total += amt

        message_lines.append("-" * 25)
        message_lines.append(f"Total = ₹{total}")

        return "\n".join(message_lines)

    except Exception as e:
        print("Error in catorgize_items:", e)
        return "❌ Error while categorizing today's expenses."


