from fastapi import FastAPI, Form
from fastapi.responses import PlainTextResponse
from twilio.rest import Client
import os

account_sid = os.getenv("account_sid")
auth_token = os.getenv("auth_token")
client = Client(account_sid, auth_token)

app = FastAPI()

@app.post("/whatsapp")
async def whatsapp_webhook(Body: str = Form(...), From: str = Form(...)):
    print(f"Message from {From}: {Body}")

    #reply to user
    client.messages.create(
    from_="whatsapp:+14155238886",
    to="whatsapp:+918125056526",
    body=f"Received the message: {Body}"
    )

    return PlainTextResponse("OK")

