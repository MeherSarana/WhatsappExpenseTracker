from fastapi import APIRouter, Request
from util_functions.utilities import *
from src.services.user_registration import * # includes: src.config.db import * && src.integrations.twilio_works import * 
from twilio.base.exceptions import TwilioRestException
import time
from fastapi.responses import PlainTextResponse, HTMLResponse

router = APIRouter()

@router.post("/whatsapp")
# async def whatsapp_webhook(Body: str = Form(...), From: str = Form(...)):
async def whatsapp_webhook(request:Request):

    form_data= await request.form()
    fdata=dict(form_data)

    From= fdata.get("From") # gives: "whatsapp:+91xxxxxxxxxx"
    Body= fdata.get("Body")
    To= fdata.get("To")
    print(f"Message from {From}: {Body}")

    cln_number= clean_number(From)
    supclient = await get_supabase()
    ###############
    if not await check_if_user_exists(supclient, cln_number):
        await register_user(supclient, cln_number)
        print("Welcome message sent! to",cln_number)
    ###############
    else:
        if Body.startswith("/"):
            cmd = Body.split()[0].lower()
            if cmd == "/help":
                reply1 = handle_help()
            elif cmd == "/totalexpenseuntilnow":
                reply1 = await handle_total_today(supclient, cln_number)
            elif cmd == "/categorize_items":
                reply1 = await catorgize_items(supclient,cln_number)
            elif cmd == "/delete_account":
                reply1 = await handle_delete_account(supclient, cln_number, Body)
            else:
                reply1 = "Unknown command. Type /help to see available commands."+ "\n" + handle_help()
        else:
            parsed_msg= parse_expense_message_by_line(Body)
            reply1=format_expense_message(parsed_msg)

            try:
                supclient = await get_supabase()
                for item,amt in parsed_msg:
                    await supclient.table("expenses_record").insert({
                        "mobile_number":cln_number,
                        "item_name":item,
                        "amount":amt,
                        "timestamp":int(time.time())
                    }).execute()
            except Exception as e:
                print("Supabase error: ",e)
            print("HelloTest")

        #################################################################################################
        # replying with a formatted response of the expenses sent by user
        try:
            await send_whatsapp_message(
                from_=To,
                to=From,
                body=reply1
            )
        except TwilioRestException as e:
            print("Twilio error: ",e)
        #################################################################################################
        # #simple reply to user
        # try:
        #     await send_whatsapp_message(
        #         from_=To,
        #         to=From,
        #         body=f"Received your message: {Body}"
        #     )
        # except TwilioRestException as e:
        #     print("Twilio error: ",e)
        #################################################################################################
        # return PlainTextResponse("OK")

        #################################################################################################