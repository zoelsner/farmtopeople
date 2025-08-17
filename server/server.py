import json
import os
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, Form, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, PlainTextResponse
import vonage
from dotenv import load_dotenv
# Add paths for imports
import sys
import os
import importlib
sys.path.insert(0, os.path.dirname(__file__))  # For server directory imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))  # For scrapers

# Direct imports from the server directory
import supabase_client as db
import meal_planner
# Import our current primary scraper
from scrapers.customize_scraper import main as run_cart_scraper

# Load .env file from the project root
from pathlib import Path
project_root = Path(__file__).parent.parent
load_dotenv(dotenv_path=project_root / '.env')


app = FastAPI()

@app.get("/health")
async def health_check():
    """Health check endpoint for Railway"""
    return {"status": "healthy", "service": "farmtopeople-sms"}

DATA_DIR = Path(".")

# Vonage Client for sending messages
vonage_client = vonage.Client(
    key=os.getenv("VONAGE_API_KEY"),
    secret=os.getenv("VONAGE_API_SECRET")
)

def run_full_meal_plan_flow(phone_number: str):
    """
    This function runs in the background. It scrapes the user's cart,
    generates a meal plan, formats it, and sends it as an SMS.
    """
    print(f"🚀 BACKGROUND: Starting full meal plan flow for {phone_number}")
    print(f"🔧 DEBUG: Available env vars: VONAGE_API_KEY={bool(os.getenv('VONAGE_API_KEY'))}, VONAGE_PHONE_NUMBER={os.getenv('VONAGE_PHONE_NUMBER')}")
    
    # Step 0: Look up user credentials from Supabase
    print(f"🔍 Looking up user credentials for {phone_number}")
    
    # Normalize phone number format - try multiple formats
    phone_formats = [phone_number, f"+{phone_number}", f"1{phone_number}" if not phone_number.startswith('1') else phone_number]
    user_data = None
    
    try:
        for phone_format in phone_formats:
            user_data = db.get_user_by_phone(phone_format)
            if user_data:
                print(f"✅ User found with format: {phone_format}")
                # Add a print statement to confirm what's found
                print(f"   Email: {user_data.get('ftp_email')}, Password: {'******' if user_data.get('ftp_password') else 'Not found'}")
                break
        
        if not user_data:
            print(f"❌ No user found for phone number {phone_number}")
            print("   User needs to register first by texting 'new' or visiting the login link")
            # Still try to run scraper without credentials for basic functionality
            user_data = {}
    except Exception as e:
        print(f"❌ Error looking up user: {e}")
        user_data = {}
    
    # Step 1: Run the complete cart scraper
    print(f"🔍 Running complete cart scraper for user: {phone_number}")
    try:
        if user_data and user_data.get('ftp_email') and user_data.get('ftp_password'):
            print("🔐 Credentials found. Setting environment variables for scraper.")
            os.environ['EMAIL'] = user_data['ftp_email']
            os.environ['PASSWORD'] = user_data['ftp_password']
        else:
            print("⚠️ No credentials found for this user. Scraper will run without login.")
            # Ensure env vars are not set from a previous run
            if 'EMAIL' in os.environ: del os.environ['EMAIL']
            if 'PASSWORD' in os.environ: del os.environ['PASSWORD']

        run_cart_scraper()
        print("✅ Cart scraping completed successfully")
    except Exception as e:
        print(f"❌ Cart scraping failed: {e}")
        # Clean up env vars
        if 'EMAIL' in os.environ: del os.environ['EMAIL']
        if 'PASSWORD' in os.environ: del os.environ['PASSWORD']
        return # Stop the flow if scraping fails

    # Clean up environment variables immediately after use
    if 'EMAIL' in os.environ: del os.environ['EMAIL']
    if 'PASSWORD' in os.environ: del os.environ['PASSWORD']

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
    print(f"SMS body length: {len(sms_body)} characters")
    print(f"SMS preview: {sms_body[:100]}...")
    try:
        # Remove the + prefix for Vonage API (like we do in the immediate reply)
        to_number = phone_number.lstrip("+")
        from_number = os.getenv("VONAGE_PHONE_NUMBER", "12019773745")
        # Ensure the from number has country code
        if not from_number.startswith("1"):
            from_number = "1" + from_number
        
        print(f"📱 DEBUG: Sending SMS from={from_number} to={to_number}")
        print(f"📝 DEBUG: Message length={len(sms_body)} chars")
        
        response = vonage_client.sms.send_message({
            "from": from_number,  # Use 'from' not 'from_'
            "to": to_number,
            "text": sms_body
        })
        print(f"✅ SMS sent successfully: {response}")
    except Exception as e:
        print(f"❌ Error sending SMS: {e}")
        print(f"🔧 DEBUG: Vonage client config - API key exists: {bool(os.getenv('VONAGE_API_KEY'))}")

@app.get("/healthz", status_code=200)
def health_check():
    """Health check endpoint to confirm the server is running."""
    return {"status": "ok"}

@app.get("/sms/incoming")
@app.post("/sms/incoming")
async def sms_incoming(request: Request, background_tasks: BackgroundTasks, msisdn: str = None, text: str = None):
    """
    Handles incoming SMS messages from Vonage.
    This is the main entry point for user interaction.
    """
    # Handle GET, POST form, and JSON-POST requests from Vonage
    if request.method == "GET":
        # Vonage sends via query parameters
        query_params = request.query_params
        user_phone_number = "+" + query_params.get("msisdn", "")
        user_message = query_params.get("text", "").lower().strip()
        print(f"GET request - Phone: {user_phone_number}, Message: '{user_message}'")
    else:
        # POST request - try JSON first, then form data
        try:
            json_data = await request.json()
            user_phone_number = "+" + json_data.get("msisdn", "")
            user_message = json_data.get("text", "").lower().strip()
            print(f"JSON-POST request - Phone: {user_phone_number}, Message: '{user_message}'")
            print(f"📋 JSON data received: {json_data}")
        except:
            # Fallback to form data (current method)
            user_phone_number = "+" + (msisdn or "")
            user_message = (text or "").lower().strip()
            print(f"Form POST request - Phone: {user_phone_number}, Message: '{user_message}'")

    print(f"Received message from {user_phone_number}: '{user_message}'")

    # --- Main App Logic Router ---
    base_url = str(request.base_url).rstrip('/')

    if "hello" in user_message:
        reply = "Hi there! I'm your Farm to People meal planning assistant. How can I help?"
    elif "plan" in user_message:
        # Acknowledge immediately
        reply = "Thank you for your text! 📱 We are preparing your personalized meal plan now. Please wait a moment while we analyze your cart contents... 🛒✨"
        # Add the scraping/planning job to the background
        print(f"🎯 Adding background task for meal plan flow: {user_phone_number}")
        try:
            background_tasks.add_task(run_full_meal_plan_flow, user_phone_number)
            print(f"✅ Background task added successfully")
        except Exception as e:
            print(f"❌ Error adding background task: {e}")
            reply = "Thank you for your text! 📱 We're experiencing a technical issue. Please try again in a moment."
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

    # Send immediate reply via Vonage
    try:
        # Remove the + prefix for Vonage API
        to_number = user_phone_number.lstrip("+")
        response = vonage_client.sms.send_message({
            "from": "1" + os.getenv("VONAGE_PHONE_NUMBER", "2019773745"),  # Ensure country code
            "to": to_number,
            "text": reply
        })
        print(f"✅ Immediate SMS reply sent: {response}")
    except Exception as e:
        print(f"❌ Error sending immediate SMS reply: {e}")

    # Return 200 OK to Vonage
    return {"status": "ok"}


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
    import os
    # To run this server locally, use the command:
    # uvicorn server:app --reload
    port = int(os.getenv("PORT", 8000))
    print(f"Starting server on port {port}... To test locally, run 'uvicorn server:app --reload' in your terminal.")
    # This part is for local development and won't be used in production
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)
