import json
import os
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, Form, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, PlainTextResponse
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
from dotenv import load_dotenv
import supabase_client as db

import meal_planner
import farmbox_optimizer

# More explicit .env loading
from pathlib import Path
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)


app = FastAPI()

DATA_DIR = Path(".")

# Twilio Client for sending messages
twilio_client = Client(os.getenv("TWILIO_ACCOUNT_SID"), os.getenv("TWILIO_AUTH_TOKEN"))

def run_full_meal_plan_flow(phone_number: str):
    """
    This function runs in the background. It scrapes the user's cart,
    generates a meal plan, formats it, and sends it as an SMS.
    """
    print(f"BACKGROUND: Starting full meal plan flow for {phone_number}")
    
    # Step 1: Run the scraper
    # Note: We'll need to adapt the scraper to be importable and run without user input.
    # For now, let's assume it runs and we get a new cart file.
    farmbox_optimizer.scan_farm_box(phone_number)
    
    # Step 2: Run the meal planner with the new data
    plan = meal_planner.run_main_planner() # We'll create this helper function
    
    # Step 3: Format the plan for SMS
    if not plan or not plan.get("meals"):
        sms_body = "Sorry, I had trouble generating a meal plan. Please try again later."
    else:
        sms_body = "🍽️ Your Farm to People meal plan is ready!\n\n"
        for meal in plan['meals']:
            sms_body += f"- {meal['title']}\n"
        sms_body += "\nEnjoy your meals!"

    # Step 4: Send the final SMS
    print(f"BACKGROUND: Sending final meal plan SMS to {phone_number}")
    twilio_client.messages.create(
        body=sms_body,
        from_=os.getenv("TWILIO_PHONE_NUMBER"),
        to=phone_number
    )

@app.get("/healthz", status_code=200)
def health_check():
    """Health check endpoint to confirm the server is running."""
    return {"status": "ok"}

@app.post("/sms")
async def sms_reply(background_tasks: BackgroundTasks, From: str = Form(...), Body: str = Form(...)):
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
        # Acknowledge immediately
        reply = "Got it! I'm analyzing your latest cart contents now. Your personalized meal plan will arrive in a new message in just a moment..."
        # Add the scraping/planning job to the background
        background_tasks.add_task(run_full_meal_plan_flow, user_phone_number)
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
        reply = "Sorry, I didn't understand that. Text 'plan' for meal ideas."

    # Add the reply to the TwiML response
    resp.message(reply)

    # Return the response as XML
    # Use the `str()` function on the response object to get the TwiML XML
    return str(resp)


@app.get("/login", response_class=HTMLResponse)
def login_form(phone: str = ""):
    """Simple HTML form to collect FTP credentials securely over HTTPS."""
    phone_safe = phone
    # More detailed HTML with CSS to match the Farm to People aesthetic
    return f"""
<!doctype html>
<html>
  <head>
    <meta charset='utf-8'/>
    <meta name='viewport' content='width=device-width, initial-scale=1'/>
    <title>Connect Farm to People</title>
    <style>
      body {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        padding: 24px;
        max-width: 480px;
        margin: 40px auto;
        background-color: #f9f8f6; /* A common off-white color */
        color: #333;
      }}
      .container {{
        background-color: #fff;
        padding: 2rem;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
      }}
      h2 {{
        font-size: 24px;
        color: #2a6e3f; /* A dark green similar to FTP's branding */
        margin-bottom: 8px;
      }}
      .hint {{
        color: #666;
        font-size: 14px;
        margin-bottom: 24px;
      }}
      form {{
        display: grid;
        gap: 16px;
      }}
      label {{
        font-weight: 600;
        font-size: 14px;
      }}
      input[type='email'], input[type='password'] {{
        width: 100%;
        padding: 12px;
        font-size: 16px;
        border: 1px solid #ccc;
        border-radius: 4px;
        box-sizing: border-box; /* Important for padding */
        margin-top: 4px;
      }}
      button {{
        padding: 14px 12px;
        font-size: 16px;
        font-weight: 700;
        background-color: #2a6e3f; /* Matching green */
        color: #fff;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        transition: background-color 0.2s;
      }}
      button:hover {{
        background-color: #1e512d; /* A darker green for hover */
      }}
    </style>
  </head>
  <body>
    <div class="container">
      <h2>Connect your Account</h2>
      <p class='hint'>Your credentials are used only to fetch your cart for meal planning and are stored securely.</p>
      <form method='post' action='/login'>
        <input type='hidden' name='phone' value='{phone_safe}'/>
        <div>
          <label for="email">Email</label>
          <input required type='email' id='email' name='email' placeholder='you@example.com'/>
        </div>
        <div>
          <label for="password">Password</label>
          <input required type='password' id='password' name='password' placeholder='••••••••'/>
        </div>
        <button type='submit'>Save & Connect</button>
      </form>
    </div>
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

# This is a new test endpoint
@app.post("/test-full-flow")
async def test_full_flow(background_tasks: BackgroundTasks):
    """
    An endpoint for manually triggering the full pipeline for testing.
    Uses the default phone number from the .env file.
    """
    test_phone_number = os.getenv("YOUR_PHONE_NUMBER")
    if not test_phone_number:
        return {"status": "error", "message": "YOUR_PHONE_NUMBER not set in .env"}

    print(f"--- TRIGGERING FULL FLOW FOR {test_phone_number} ---")
    background_tasks.add_task(run_full_meal_plan_flow, test_phone_number)
    return {"status": "ok", "message": f"Meal planning process started for {test_phone_number}. The result will be sent via SMS."}

if __name__ == "__main__":
    import uvicorn
    # To run this server locally, use the command:
    # uvicorn server:app --reload
    print("Starting server... To test, run 'uvicorn server:app --reload' in your terminal.")
    # This part is for local development and won't be used in production
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
