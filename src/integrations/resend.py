import os
import asyncio
import resend
from import_env import *

api_key = os.getenv("RESEND_API_KEY")
resend.api_key = api_key

async def send_email(to_email: str, subject: str, html_body: str):
    try:
        params = {
            "from": "MyHisab <onboarding@resend.dev>",
            "to": [to_email],
            "subject": subject,
            "html": html_body,
        }
        # Run the blocking send in a thread
        result = await asyncio.to_thread(resend.Emails.send, params)
        print(f"📧 Email sent to {to_email}")
        return result
    except Exception as e:
        print("Error sending email:", str(e))
        return None


