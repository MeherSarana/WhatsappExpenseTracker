from fastapi import FastAPI, Form, Request
from fastapi.responses import PlainTextResponse, HTMLResponse
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import os
import time
from supabase import create_async_client, Client as SupabaseClient
from dotenv import load_dotenv

load_dotenv("keys.env")
account_sid=os.getenv("account_sid")
auth_token=os.getenv("auth_token")
client= Client(account_sid,auth_token)

supabase_url=os.getenv("supabase_url")
supabase_key=os.getenv("supabase_key")

async def init_supabase():
    return await create_async_client(supabase_url, supabase_key)

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
        amount = None
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
    # sample result: [('apple', 50), ('led bulb', 60), ('kiwi', 70)]

def format_expense_message(expense_list):
    col_width = 19  # width of the item-name column
    lines = []

    # Header
    lines.append(f"{'Item-name'.ljust(col_width)}Amount")
    lines.append('-' * (col_width + 6))

    for item, amt in expense_list:
        if len(item) <= col_width:
            lines.append(f"{item.ljust(col_width)}{amt}")
        else:
            # wrap long item names
            words = item.split()
            line = ""
            first_line = True
            for word in words:
                if len(line + (' ' if line else '') + word) <= col_width:
                    line += (' ' if line else '') + word
                else:
                    if first_line:
                        lines.append(f"{line.ljust(col_width)}{amt}")
                        first_line = False
                    else:
                        lines.append(line.ljust(col_width))
                    line = word
            # remaining words
            if first_line:
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

    resp1= parse_expense_message_by_line(Body)
    reply1=format_expense_message(resp1)
    cln_number= clean_number(From)

    try:
        supabase = await init_supabase()
        for item,amt in resp1:
            await supabase.table("expenses_record").insert({
                "mobile_number":cln_number,
                "item_name":item,
                "amount":amt,
                "timestamp":int(time.time())
            }).execute()
    except Exception as e:
        print("Supabase error: ",e)
    print("HelloTest")
    # #replying with a formatted response
    # try:
    #     client.messages.create(
    #         from_=To,
    #         to=From,
    #         body=reply1
    #     )

    # except TwilioRestException as e:
    #     print("Twilio error: ",e)

    # #simple reply to user
    # try:
    #     client.messages.create(
    #         from_=To,
    #         to=From,
    #         body=f"Got your msg: {Body}"
    #     )
    # except TwilioRestException as e:
    #     print("Twilio error: ",e)

    # return PlainTextResponse("OK")