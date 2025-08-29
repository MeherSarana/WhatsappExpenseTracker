# importing supabase and twilio functionalities

from src.integrations.twilio_works import * # includes: from src.config.db import * && from import_env import *
from util_functions.utilities import generate_TOTP_secret, current_epoch_time

twil_number = os.getenv("twilio_number")

# To register new user into the "users" table in supabase
async def register_user(supclient, mobile):
    TOTP_secret = generate_TOTP_secret()
    current_epoch = current_epoch_time()
    data = {
        "mobile_number": mobile,
        "registered_at":current_epoch,
        "totp_secret":TOTP_secret
    }
    await supclient.table("users").insert(data).execute()

    # Send welcome message using Twilio
    await send_whatsapp_message(
        from_=f"whatsapp:{twil_number}",   # Twilio sandbox / business number
        to=f"whatsapp:{mobile}",
        # body=(
        #     "🎉 Welcome to the WhatsApp Expense Tracker!\n\n"
        #     "You can now start adding your expenses.\n"
        #     "👉 Example: 'Apple 50'\n"
        #     "👉 At the end of the day, you'll receive your daily summary.\n\n"
        #     "Type /help to see all available commands."
        # ) ✅ ❌
        body=(
            "🎉 Welcome to the WhatsApp Expense Tracker!\n\n"
            "You can now start adding your expenses.\n"
            "Guidelines-Examples for sending expenses:\n"
            "Apple 50 ✅\n"
            "50 Apple ✅\n\n"
            "Wheat 5kg 100 ✅\n"
            "100 Wheat 5kg ✅\n\n"
            "Wheat 5 kg 100 ✅"
            "100 Wheat 5 kg ❌"
            "🌟 At the end of the day, you'll receive your daily summary.\n\n"
            "Type /help to see all available commands."
        )
    )
    return True