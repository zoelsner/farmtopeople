import json
import os
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv
import supabase_client as db

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

DATA_DIR = Path(".")

@app.get("/healthz", status_code=200)
def health_check():
    """Health check endpoint to confirm the server is running."""
    return {"status": "ok"}

@app.post("/sms")
async def sms_reply(request: Request, From: str = Form(...), Body: str = Form(...)):
    """
    Handles incoming SMS messages from Twilio.
    This is the main entry point for user interaction.
    """
    user_phone_number = From
    user_message = Body.lower().strip()

    print(f"Received message from {user_phone_number}: '{user_message}'")

    # Initialize the response object
    resp = MessagingResponse()

    # --- Main App Logic Router ---
    base_url = str(request.base_url).rstrip('/')

    if "hello" in user_message:
        reply = "Hi there! I'm your Farm to People meal planning assistant. How can I help?"
    elif "plan" in user_message:
        # TODO: Trigger the meal planner logic
        reply = "I'm ready to help you plan! First, I'll check your latest cart contents..."
    elif "new" in user_message:
        # Intake start. Also offer secure link to provide login.
        login_link = f"{base_url}/login?phone={quote(user_phone_number)}"
        reply = (
            "Welcome! Let's get you set up. What's your cooking style?\n\n"
            f"To connect your Farm to People account securely, you can also use this link: {login_link}"
        )
    elif "login" in user_message or "email" in user_message:
        login_link = f"{base_url}/login?phone={quote(user_phone_number)}"
        reply = f"To securely provide your FTP email & password, open: {login_link}"
    else:
        reply = "Sorry, I didn't understand that. You can say 'plan' to get meal ideas or 'new' if you're a new user."

    # Add the reply to the TwiML response
    resp.message(reply)

    # Return the response as XML
    # Use the `str()` function on the response object to get the TwiML XML
    return str(resp)


@app.get("/login", response_class=HTMLResponse)
def login_form(phone: str = ""):
    """Simple HTML form to collect FTP credentials securely over HTTPS."""
    phone_safe = phone
    return f"""
<!doctype html>
<html>
  <head>
    <meta charset='utf-8'/>
    <meta name='viewport' content='width=device-width, initial-scale=1'/>
    <title>Connect Farm to People</title>
    <style>
      body {{ font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif; padding: 24px; max-width: 640px; margin: auto; }}
      form {{ display: grid; gap: 12px; }}
      input, button {{ padding: 10px 12px; font-size: 16px; }}
      .hint {{ color: #666; font-size: 14px; }}
    </style>
  </head>
  <body>
    <h2>Connect your Farm to People account</h2>
    <p class='hint'>Your credentials are used only to fetch your cart for meal planning. You can remove them anytime.</p>
    <form method='post' action='/login'>
      <input type='hidden' name='phone' value='{phone_safe}'/>
      <label>Email<br/><input required type='email' name='email' placeholder='you@example.com'/></label>
      <label>Password<br/><input required type='password' name='password' placeholder='••••••••'/></label>
      <button type='submit'>Save & Connect</button>
    </form>
  </body>
</html>
"""


@app.post("/login")
async def login_submit(phone: str = Form("") , email: str = Form(...), password: str = Form(...)):
    # Save to Supabase (upsert by email, include phone if provided)
    try:
        db.upsert_user_credentials(
            phone_number=phone or None,
            ftp_email=email,
            ftp_password=password,
            preferences=None,
        )
        return PlainTextResponse("Saved. You can now text 'plan' to get meal ideas.")
    except Exception as e:
        print(f"Supabase save error: {e}")
        return PlainTextResponse("There was an error saving your info. Please try again.", status_code=500)

if __name__ == "__main__":
    import uvicorn
    # To run this server locally, use the command:
    # uvicorn server:app --reload
    print("Starting server... To test, run 'uvicorn server:app --reload' in your terminal.")
    # This part is for local development and won't be used in production
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
