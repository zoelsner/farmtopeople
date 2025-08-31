import asyncio
import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, Form, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, PlainTextResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
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
from scrapers.comprehensive_scraper import main as run_cart_scraper

# Load .env file from the project root
from pathlib import Path
project_root = Path(__file__).parent.parent
load_dotenv(dotenv_path=project_root / '.env')

# === CONFIGURATION ===
# IMPORTANT: Change this single variable to switch between models throughout the app
# Updated 2025-08-29: Switched from hardcoded models to configurable variable
# Updated 2025-08-29: Using gpt-4o for production
AI_MODEL = "gpt-4o"  # Options: "gpt-4o", "gpt-4o-mini", "gpt-4-turbo"
print(f"🤖 AI Model configured: {AI_MODEL}")

app = FastAPI()

# Import and include meal planning API routes
from meal_planning_api import router as meal_planning_router
from test_meal_api import router as test_meal_router
app.include_router(meal_planning_router)
app.include_router(test_meal_router)

# Mount static files for serving CSS/JS assets
app.mount("/static", StaticFiles(directory="server/static"), name="static")

# Setup templates for serving HTML pages
templates = Jinja2Templates(directory="server/templates")

@app.get("/health")
async def health_check():
    """Health check endpoint for Railway"""
    return {"status": "healthy", "service": "farmtopeople-sms"}

DATA_DIR = Path(".")

# Vonage Client for sending messages
# Temporarily disabled for web endpoint testing
vonage_client = None
print("⚠️ SMS disabled for testing - web endpoint will work")

def send_progress_sms(phone_number: str, message: str):
    """Send a progress update SMS to the user"""
    try:
        to_number = phone_number.lstrip("+")
        from_number = os.getenv("VONAGE_PHONE_NUMBER", "12019773745")
        if not from_number.startswith("1"):
            from_number = "1" + from_number
        
        response = vonage_client.sms.send_message({
            "from": from_number,
            "to": to_number,
            "text": message
        })
        print(f"📱 Progress SMS sent: {message}")
    except Exception as e:
        print(f"❌ Error sending progress SMS: {e}")

async def handle_meal_plan_confirmation(phone_number: str, user_message: str, background_tasks: BackgroundTasks):
    """Handle user responses to meal plan confirmation"""
    try:
        message_lower = user_message.lower().strip()
        
        if "confirm" in message_lower:
            # User confirmed - generate detailed recipes
            reply = "✅ Perfect! Generating your detailed recipes now..."
            
            # Clear the confirmation step
            db.update_user_meal_plan_step(phone_number, None)
            
            # Start PDF recipe generation
            background_tasks.add_task(generate_confirmed_meal_plan, phone_number)
            
        elif "drop meal" in message_lower:
            # User wants to remove a specific meal
            reply = "🔄 Got it! Updating your meal plan..."
            background_tasks.add_task(handle_meal_plan_modification, phone_number, user_message)
            
        elif "no breakfast" in message_lower:
            # User doesn't want breakfast meals
            reply = "🔄 Removing breakfast meals and regenerating plan..."
            background_tasks.add_task(handle_meal_plan_modification, phone_number, user_message)
            
        else:
            # User sent custom modifications
            reply = "🔄 Processing your changes and updating the meal plan..."
            background_tasks.add_task(handle_meal_plan_modification, phone_number, user_message)
        
        # Send immediate reply
        send_progress_sms(phone_number, reply)
        return PlainTextResponse("OK", status_code=200)
        
    except Exception as e:
        print(f"❌ Error handling meal plan confirmation: {e}")
        error_reply = "❌ Error processing your response. Please try again or text 'CONFIRM' to proceed."
        send_progress_sms(phone_number, error_reply)
        return PlainTextResponse("Error", status_code=500)

def format_sms_with_help(message: str, state: str = None) -> str:
    """
    Add contextual help text to SMS messages based on conversation state.
    
    This function enhances user experience by providing relevant next-step guidance
    in every SMS response, reducing user confusion and improving engagement.
    
    Args:
        message (str): The main SMS message content
        state (str, optional): Current conversation state to determine appropriate help text.
                              If None or unknown, defaults to general help.
    
    Returns:
        str: Original message + visual separator + contextual help text
    
    Available States:
        - 'analyzing': Progress indicator during cart/meal analysis (shows timing expectation)
        - 'plan_ready': Action options after meal plan is delivered (CONFIRM/SWAP/SKIP)
        - 'greeting': Welcome state with basic navigation options
        - 'onboarding': During user registration/setup process  
        - 'login': After providing secure login link
        - 'error': Recovery options when something goes wrong
        - 'default': General help for unrecognized inputs or no state provided
    
    Example Usage:
        >>> format_sms_with_help("📦 Analyzing your cart...", 'analyzing')
        "📦 Analyzing your cart...\n━━━━━━━━━\n⏳ This takes 20-30 seconds..."
        
        >>> format_sms_with_help("Your meal plan is ready!", 'plan_ready')
        "Your meal plan is ready!\n━━━━━━━━━\n💬 Reply: CONFIRM | SWAP item | SKIP day | help"
    
    Design Notes:
        - Uses visual separator (━━━━━━━━━) to distinguish help from main message
        - Keeps help text concise for SMS length limits (typically 65-200 total chars)
        - Uses consistent emoji prefixes (⏳ for progress, 💬 for actions)
        - Provides specific actionable commands rather than vague instructions
    
    Added: August 26, 2025 - Part of Tuesday PM milestone (Week 3 implementation)
    """
    
    # Contextual help text mapped to conversation states
    # Each help text follows pattern: visual separator + emoji + specific actions
    help_text = {
        # During processing states - set expectation of time required
        'analyzing': "━━━━━━━━━\n⏳ This takes 20-30 seconds...",
        
        # After meal plan delivery - show available modification options
        'plan_ready': "━━━━━━━━━\n💬 Reply: CONFIRM | SWAP item | SKIP day | help",
        
        # Initial greeting - show primary entry points
        'greeting': "━━━━━━━━━\n💬 Text 'plan' to start | 'new' to register",
        
        # During user setup - encourage completion via web or SMS
        'onboarding': "━━━━━━━━━\n💬 Reply with your cooking preferences or use the link",
        
        # After login link provided - guide to next step
        'login': "━━━━━━━━━\n💬 After login, text 'plan' for your meal plan",
        
        # Error recovery - provide retry options and help
        'error': "━━━━━━━━━\n💬 Text 'plan' to try again | 'help' for options",
        
        # Fallback for unknown inputs or states
        'default': "━━━━━━━━━\n💬 Text 'plan' to start | 'new' to register | 'help' for options"
    }
    
    # Return original message with contextual help appended
    # Uses .get() with default fallback to handle unknown states gracefully
    return f"{message}\n{help_text.get(state, help_text['default'])}"

def generate_confirmed_meal_plan(phone_number: str):
    """Generate detailed PDF recipes after user confirmation"""
    try:
        print(f"🍳 Generating confirmed meal plan for {phone_number}")
        
        # Get user preferences
        user_data = db.get_user_by_phone(phone_number)
        skill_level = user_data.get('cooking_skill_level', 'intermediate') if user_data else 'intermediate'
        
        # Generate detailed PDF
        from pdf_meal_planner import generate_pdf_meal_plan
        pdf_path = generate_pdf_meal_plan(generate_detailed_recipes=True, user_skill_level=skill_level)
        
        if pdf_path:
            # Send PDF link
            base_url = "http://localhost:8000"  # TODO: Use actual domain
            pdf_filename = pdf_path.split('/')[-1]
            pdf_url = f"{base_url}/pdfs/{pdf_filename}"
            
            final_message = (
                "🍽️ Your personalized meal plan is ready!\n\n"
                f"📄 View your detailed recipes: {pdf_url}\n\n"
                "Each recipe includes:\n"
                "• Step-by-step cooking instructions\n"
                "• Storage tips for ingredients\n"
                "• Chef techniques and tips\n\n"
                "Happy cooking! 👨‍🍳"
            )
        else:
            final_message = "❌ Error generating your recipe PDF. Please try again with 'plan'."
        
        send_progress_sms(phone_number, final_message)
        
    except Exception as e:
        print(f"❌ Error generating confirmed meal plan: {e}")
        send_progress_sms(phone_number, "❌ Error generating recipes. Please try again.")

def handle_meal_plan_modification(phone_number: str, user_request: str):
    """Handle user requests to modify the meal plan"""
    try:
        print(f"🔄 Handling meal plan modification for {phone_number}: {user_request}")
        
        # For now, just regenerate the cart analysis
        import meal_planner
        modified_analysis = meal_planner.generate_cart_analysis_summary()
        
        confirmation_message = (
            "🔄 Here's your updated meal plan:\n\n" +
            modified_analysis
        )
        
        send_progress_sms(phone_number, confirmation_message)
        
        # Keep user in confirmation state
        db.update_user_meal_plan_step(phone_number, 'awaiting_confirmation')
        
    except Exception as e:
        print(f"❌ Error handling meal plan modification: {e}")
        send_progress_sms(phone_number, "❌ Error modifying meal plan. Please try 'CONFIRM' to proceed with original plan.")

async def run_full_meal_plan_flow(phone_number: str):
    """
    This function runs in the background. It scrapes the user's cart,
    generates a meal plan, formats it, and sends it as an SMS.
    """
    print(f"🚀 BACKGROUND: Starting full meal plan flow for {phone_number}")
    print(f"🔧 DEBUG: Available env vars: VONAGE_API_KEY={bool(os.getenv('VONAGE_API_KEY'))}, VONAGE_PHONE_NUMBER={os.getenv('VONAGE_PHONE_NUMBER')}")
    
    # Progress update 1: Starting process with timing expectation
    send_progress_sms(phone_number, format_sms_with_help("🔍 Looking up your account...", 'analyzing'))
    
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
            send_progress_sms(phone_number, "❌ Account not found. Please text 'FEED ME' to get set up first!")
            return
    except Exception as e:
        print(f"❌ Error looking up user: {e}")
        send_progress_sms(phone_number, "❌ Having trouble accessing your account. Please try again in a moment.")
        return
    
    # Progress update 2: Account status with appropriate help text
    if user_data.get('ftp_email'):
        # Account found - continue with processing indicator
        send_progress_sms(phone_number, format_sms_with_help("🔐 Found your account! Logging into Farm to People...", 'analyzing'))
    else:
        # Account setup needed - provide recovery options
        send_progress_sms(phone_number, format_sms_with_help("⚠️ No Farm to People account linked.", 'error'))
        return
    
    # Step 1: Run the complete cart scraper
    print(f"🔍 Running complete cart scraper for user: {phone_number}")
    
    # Progress update 3: Cart analysis with processing time indicator
    send_progress_sms(phone_number, format_sms_with_help("📦 Analyzing your current cart and customizable boxes...", 'analyzing'))
    
    try:
        # Pass credentials directly to scraper (thread-safe!)
        cart_data = None
        if user_data and user_data.get('ftp_email') and user_data.get('ftp_password'):
            print("🔐 Credentials found. Running personalized cart scrape...")
            credentials = {
                'email': user_data['ftp_email'],
                'password': user_data['ftp_password']
            }
            # Get cart data directly from async scraper (clean solution)
            cart_data = await run_cart_scraper(credentials, return_data=True)
            print(f"✅ Cart scraping completed: {len(cart_data.get('individual_items', [])) if cart_data else 0} items")
        else:
            print("⚠️ No credentials found for this user. Cannot scrape cart.")
            send_progress_sms(phone_number, format_sms_with_help("❌ Please connect your Farm to People account first.", 'error'))
            return
        
        # ✅ NEW: Check if user has preferences, if not collect them
        user_preferences = check_and_collect_preferences(phone_number, user_data)
        if not user_preferences:
            # Preferences collection started, will continue in another message
            return
        
        # Progress update 4: Meal plan generation with processing indicator
        send_progress_sms(phone_number, format_sms_with_help("📋 Analyzing your cart and creating strategic meal plan...", 'analyzing'))
        
        try:
            cart_analysis = meal_planner.generate_cart_analysis_summary()
            
            # Send meal plan with action options (CONFIRM/SWAP/SKIP)
            send_progress_sms(phone_number, format_sms_with_help(cart_analysis, 'plan_ready'))
            
            # Mark user as waiting for meal plan confirmation
            db.update_user_meal_plan_step(phone_number, 'awaiting_confirmation')
            
            print(f"✅ Cart analysis sent to {phone_number}, awaiting confirmation")
            return  # Stop here, wait for user confirmation
            
        except Exception as e:
            print(f"❌ Error generating cart analysis: {e}")
            send_progress_sms(phone_number, "❌ Error analyzing your cart. Please try again in a moment.")
            return
        
    except Exception as e:
        print(f"❌ Cart scraping failed: {e}")
        send_progress_sms(phone_number, "❌ Having trouble accessing your cart. Please check your Farm to People account and try again.")
        # Clean up env vars
        if 'EMAIL' in os.environ: del os.environ['EMAIL']
        if 'PASSWORD' in os.environ: del os.environ['PASSWORD']
        return # Stop the flow if scraping fails

    # Clean up environment variables immediately after use
    if 'EMAIL' in os.environ: del os.environ['EMAIL']
    if 'PASSWORD' in os.environ: del os.environ['PASSWORD']

    # Step 2: Run the meal planner with REAL cart data and user preferences!
    skill_level = user_preferences.get('cooking_skill_level', 'intermediate')
    plan = meal_planner.run_main_planner(
        cart_data=cart_data,  # Pass the actual scraped cart!
        user_preferences=user_preferences,  # Pass user preferences!
        generate_detailed_recipes=True, 
        user_skill_level=skill_level
    )
    
    # Step 2.5: Save meal suggestions to database for meal calendar consistency
    if plan and plan.get('meals'):
        try:
            # Extract meal data for storage
            meal_suggestions = []
            for meal in plan.get('meals', []):
                meal_data = {
                    'title': meal.get('title', ''),
                    'protein': meal.get('protein', ''),
                    'cook_time': meal.get('cook_time', ''),
                    'servings': meal.get('servings', 2),
                    'ingredients': meal.get('ingredients', []),
                    'instructions': meal.get('instructions', []),
                    'nutrition': meal.get('nutrition', {}),
                    'storage_tips': meal.get('storage_tips', [])
                }
                meal_suggestions.append(meal_data)
            
            # Save to database with meal suggestions
            db.save_latest_cart_data(
                phone_number=phone_number,
                cart_data=cart_data,
                meal_suggestions=meal_suggestions
            )
            print(f"✅ Saved {len(meal_suggestions)} meal suggestions to database")
        except Exception as e:
            print(f"⚠️ Failed to save meal suggestions: {e}")
            # Continue even if saving fails
    
    # Step 3: Generate PDF meal plan (now with professional recipes)
    pdf_path = None
    try:
        from pdf_meal_planner import generate_pdf_meal_plan
        # PDF generator will now use the enhanced meal plan with detailed recipes
        pdf_path = generate_pdf_meal_plan(generate_detailed_recipes=True, user_skill_level="intermediate")
        if pdf_path:
            print(f"✅ PDF generated with professional recipes: {pdf_path}")
        else:
            print("⚠️ PDF generation failed, will send text version")
    except Exception as e:
        print(f"❌ PDF generation error: {e}")
        pdf_path = None
    
    # Step 4: Format the plan for SMS
    if pdf_path:
        # Send link to PDF instead of text
        base_url = "http://localhost:8000"  # TODO: Use actual domain
        pdf_filename = pdf_path.split('/')[-1]
        pdf_url = f"{base_url}/pdfs/{pdf_filename}"
        sms_body = f"🍽️ Your professional Farm to People meal plan is ready!\n\n📄 View your complete plan with storage tips and recipes: {pdf_url}\n\nEnjoy your meals!"
    elif not plan or not plan.get("meals"):
        sms_body = "Sorry, I had trouble generating a meal plan. Please try again later."
    else:
        sms_body = "🍽️ Your Farm to People meal plan is ready!\n\n"
        for meal in plan['meals']:
            sms_body += f"- {meal['title']}\n"
        sms_body += "\nEnjoy your meals!"

    # Step 5: Send the final SMS
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

    # Check if user is in meal plan confirmation flow
    try:
        user_data = db.get_user_by_phone(user_phone_number)
        if user_data and user_data.get('meal_plan_step') == 'awaiting_confirmation':
            # Handle meal plan confirmation responses
            return await handle_meal_plan_confirmation(user_phone_number, user_message, background_tasks)
    except Exception as e:
        print(f"⚠️ Error checking meal plan step: {e}")

    if "hello" in user_message:
        # Welcome message with basic navigation help
        reply = format_sms_with_help(
            "Hi there! I'm your Farm to People meal planning assistant.", 
            'greeting'
        )
    elif "plan" in user_message:
        # Immediate acknowledgment with progress indicator and timing expectation
        reply = format_sms_with_help(
            "📦 Analyzing your Farm to People cart...", 
            'analyzing'
        )
        # Add the scraping/planning job to the background
        print(f"🎯 Adding background task for meal plan flow: {user_phone_number}")
        try:
            background_tasks.add_task(run_full_meal_plan_flow, user_phone_number)
            print(f"✅ Background task added successfully")
        except Exception as e:
            print(f"❌ Error adding background task: {e}")
            # Technical error with recovery options
            reply = format_sms_with_help(
                "We're experiencing a technical issue. Please try again in a moment.", 
                'error'
            )
    elif "new" in user_message:
        # New user registration with secure web link for credential collection
        login_link = f"{base_url}/login?phone={quote(user_phone_number)}"
        reply = format_sms_with_help(
            f"Welcome! Let's get you set up.\n\nTo connect your Farm to People account securely: {login_link}",
            'onboarding'
        )
    elif "login" in user_message or "email" in user_message:
        # User requesting login help - provide secure credential collection link
        login_link = f"{base_url}/login?phone={quote(user_phone_number)}"
        reply = format_sms_with_help(
            f"To securely provide your FTP credentials: {login_link}",
            'login'
        )
    else:
        # Fallback for unrecognized input with general help options
        reply = format_sms_with_help(
            "Sorry, I didn't understand that.",
            'default'
        )

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

# Serve PDF files
@app.get("/pdfs/{filename}")
async def serve_pdf(filename: str):
    """Serve PDF meal plans"""
    from fastapi.responses import FileResponse
    import os
    
    pdf_path = f"../pdfs/{filename}"
    if os.path.exists(pdf_path):
        return FileResponse(pdf_path, media_type="application/pdf", filename=filename)
    else:
        return PlainTextResponse("PDF not found", status_code=404)


def parse_analysis_to_html(content: str) -> str:
    """
    Parse GPT-5 analysis content into properly formatted HTML
    matching the quality of preview_analysis.html
    """
    
    # Split content into sections
    sections = content.split('### ')
    html_parts = []
    
    for i, section in enumerate(sections):
        if i == 0:
            # First section is the main title
            if section.strip().startswith('## '):
                continue
            
        if not section.strip():
            continue
            
        lines = section.strip().split('\n')
        section_title = lines[0] if lines else ""
        section_content = '\n'.join(lines[1:]) if len(lines) > 1 else ""
        
        if 'Current Cart Overview' in section_title:
            html_parts.append(format_cart_overview_section(section_content))
        elif 'Recommended Swaps' in section_title:
            html_parts.append(format_swaps_section(section_content))
        elif 'Strategic Meal Plan' in section_title:
            html_parts.append(format_meals_section(section_content))
        elif 'Recommended Protein Additions' in section_title:
            html_parts.append(format_proteins_section(section_content))
        elif 'Additional Fresh Items' in section_title:
            html_parts.append(format_shopping_section(section_title, section_content))
        elif 'Pantry Staples' in section_title:
            html_parts.append(format_shopping_section(section_title, section_content))
        elif 'Summary' in section_title:
            html_parts.append(format_summary_section(section_content))
        else:
            # Generic section
            html_parts.append(f'<h2>{section_title}</h2><div>{format_generic_content(section_content)}</div>')
    
    return '\n'.join(html_parts)

def clean_cart_item(item_text: str) -> str:
    """Clean up cart item text to be consistent and neat"""
    # Extract quantity/size info before cleaning
    quantity = ""
    quantity_match = re.search(r'\(([\d.-]+\s*(?:lb|lbs|oz|pieces?|bunch|pint|dozen))\)', item_text)
    if not quantity_match:
        # Try to find qty format
        qty_match = re.search(r'\bqty[:\s]+(\d+)', item_text)
        if qty_match:
            quantity = f"({qty_match.group(1)} pieces)"
    else:
        quantity = f"({quantity_match.group(1)})"
    
    # Remove all parenthetical content for cleaning
    item_text = re.sub(r'\([^)]*\)', '', item_text)
    
    # Clean up redundant text patterns
    item_text = re.sub(r'(?i)\bboneless,?\s*skinless\s*', '', item_text)
    item_text = re.sub(r';\s*duplicates.*', '', item_text, flags=re.IGNORECASE)
    
    # Trim and clean
    item_text = item_text.strip()
    
    # Ensure proper capitalization
    words = []
    for word in item_text.split():
        if word == '&' or word.lower() in ['and', 'or', 'with']:
            words.append(word)
        else:
            # Capitalize first letter of significant words
            words.append(word[0].upper() + word[1:] if len(word) > 1 else word.upper())
    
    result = ' '.join(words)
    
    # Add quantity back if we have it
    if quantity:
        result += f" {quantity}"
    
    return result

def format_cart_overview_section(content: str) -> str:
    """Format cart overview with proper styling"""
    html = '<h2>Current Cart Overview</h2>'
    
    # Parse the content more intelligently - handle both bulleted and indented lists
    lines = content.strip().split('\n')
    current_category = None
    items = {'Proteins': [], 'Vegetables': [], 'Fruits': []}
    
    for line in lines:
        # Check for category headers - handle both old and new formats
        if line.strip() == '- Proteins:' or line.strip() == '**Proteins:**':
            current_category = 'Proteins'
        elif line.strip() == '- Vegetables:' or line.strip() == '**Vegetables:**':
            current_category = 'Vegetables'
        elif line.strip() == '- Fruits:' or line.strip() == '**Fruits:**':
            current_category = 'Fruits'
        # Handle items that are indented with two spaces and a dash
        elif line.startswith('  - ') and current_category:
            item_text = line[4:].strip()
            # Clean up the item text for current cart (no prices)
            item_text = clean_cart_item(item_text)
            items[current_category].append(item_text)
        # Handle items with single dash (for new format)
        elif line.startswith('- ') and current_category and not any(cat in line for cat in ['Proteins:', 'Vegetables:', 'Fruits:']):
            item_text = line[2:].strip()
            # Clean up the item text for current cart (no prices)
            item_text = clean_cart_item(item_text)
            items[current_category].append(item_text)
    
    # Build HTML for each category that has items
    for category in ['Proteins', 'Vegetables', 'Fruits']:
        if items[category]:
            html += f'\n        <h3>{category}:</h3>\n        <ul>'
            for item in items[category]:
                html += f'\n            <li>{item}</li>'
            html += '\n        </ul>'
    
    return html

def format_swaps_section(content: str) -> str:
    """Format swap recommendations with highlight boxes"""
    html = '<h2>Recommended Swaps for Better Meal Flexibility</h2>'
    
    # Split into individual swaps - look for both Priority and Optional swaps
    all_swaps = re.findall(r'(?:Priority Swap #\d+|Optional Swap #\d+):.*?(?=(?:Priority Swap #\d+|Optional Swap #\d+):|$)', content, re.DOTALL)
    
    if not all_swaps:
        # Try alternative format without numbers
        all_swaps = re.findall(r'(?:Priority Swap|Optional Swap).*?(?=(?:Priority Swap|Optional Swap)|$)', content, re.DOTALL)
    
    for swap in all_swaps:
        lines = swap.strip().split('\n')
        if lines:
            # Parse the title line which contains the swap
            title_line = lines[0]
            # Ensure arrows are properly formatted
            title_line = title_line.replace('->', '→')
            
            # Find reasoning in subsequent lines
            reasoning = ""
            for line in lines[1:]:
                if line.strip().startswith('Reasoning:'):
                    reasoning = line.strip()
                elif line.strip() and not line.strip().startswith(('Priority', 'Optional')):
                    # Sometimes reasoning is on next line without "Reasoning:" prefix
                    if not reasoning:
                        reasoning = "Reasoning: " + line.strip()
            
            html += f'''
            <div class="swap-item">
                <strong>{title_line}</strong><br>
                <em>{reasoning}</em>
            </div>
            '''
    
    return html

def format_meals_section(content: str) -> str:
    """Format meal plans with meal cards"""
    html = '<h2>Strategic Meal Plan (5 balanced meals)</h2>'
    
    # Find individual meals
    meals = re.findall(r'Meal \d+:.*?(?=Meal \d+:|Notes to prevent|$)', content, re.DOTALL)
    
    for meal in meals:
        lines = meal.strip().split('\n')
        if lines:
            title = lines[0].replace('Meal ', 'Meal ')
            
            using_line = ""
            status_line = ""
            
            for line in lines[1:]:
                if line.startswith('Using:'):
                    using_line = line
                elif line.startswith('Status:'):
                    status_line = line
            
            html += f'''
            <div class="meal-item">
                <strong>{title}</strong><br>
                {f'<em>{using_line}</em><br>' if using_line else ''}
                {f'<span class="status-complete">{status_line}</span>' if status_line else ''}
            </div>
            '''
    
    # Add notes if present
    if 'Notes to prevent waste' in content:
        notes_section = content.split('Notes to prevent waste:')[1] if 'Notes to prevent waste:' in content else ""
        if notes_section:
            html += '<h3>Notes to prevent waste:</h3>'
            html += format_generic_content(notes_section.split('###')[0])  # Only until next section
    
    return html

def format_proteins_section(content: str) -> str:
    """Format protein recommendations with pricing"""
    html = '<h2>Recommended Protein Additions to Cart</h2>'
    html += '<p><strong>Healthy protein options (no beef):</strong></p><ul>'
    
    lines = content.strip().split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('- '):
            item = line[2:].strip()
            # Better formatting: separate protein name from pricing
            # Match patterns like ($16.99, 8 oz) or just ($8.99)
            if '($' in item:
                # Split at the pricing part
                parts = re.split(r'(\([^)]*\$[^)]*\))', item)
                if len(parts) >= 2:
                    protein_name = parts[0].strip()
                    pricing_part = parts[1] if len(parts) > 1 else ""
                    description = parts[2].strip() if len(parts) > 2 else ""
                    
                    # Format with better styling
                    formatted_item = protein_name
                    if pricing_part:
                        formatted_item += f' <span class="pricing">{pricing_part}</span>'
                    if description:
                        formatted_item += f' {description}'
                    
                    html += f'<li>{formatted_item}</li>'
                else:
                    html += f'<li>{item}</li>'
            else:
                html += f'<li>{item}</li>'
        elif line and not line.startswith(('Healthy protein', '#', '*')):
            # Sometimes items are listed without dashes
            item = line.strip()
            if item and ('$' in item or 'salmon' in item.lower() or 'chicken' in item.lower() or 'turkey' in item.lower()):
                if '($' in item:
                    parts = re.split(r'(\([^)]*\$[^)]*\))', item)
                    if len(parts) >= 2:
                        protein_name = parts[0].strip()
                        pricing_part = parts[1] if len(parts) > 1 else ""
                        description = parts[2].strip() if len(parts) > 2 else ""
                        
                        formatted_item = protein_name
                        if pricing_part:
                            formatted_item += f' <span class="pricing">{pricing_part}</span>'
                        if description:
                            formatted_item += f' {description}'
                        
                        html += f'<li>{formatted_item}</li>'
                    else:
                        html += f'<li>{item}</li>'
                else:
                    html += f'<li>{item}</li>'
    
    html += '</ul>'
    return html

def format_shopping_section(title: str, content: str) -> str:
    """Format shopping lists with pricing highlights"""
    html = f'<h2>{title}</h2><ul>'
    
    lines = content.strip().split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('- '):
            item = line[2:].strip()
            # Highlight pricing - match various formats
            item = re.sub(r'\((\$[0-9,.]+(?: [^)]+)?)\)', r'<span class="pricing">(\1)</span>', item)
            html += f'<li>{item}</li>'
        elif line and not line.startswith('#') and not any(skip in line.lower() for skip in ['pantry', 'fresh', 'additional', 'needed']):
            # Handle items without dashes
            item = line.strip()
            if item:
                item = re.sub(r'\((\$[0-9,.]+(?: [^)]+)?)\)', r'<span class="pricing">(\1)</span>', item)
                html += f'<li>{item}</li>'
    
    html += '</ul>'
    return html

def format_summary_section(content: str) -> str:
    """Format summary section"""
    html = '<h2>Summary</h2>'
    html += format_generic_content(content)
    return html

def format_generic_content(content: str) -> str:
    """Format generic content with basic styling"""
    # Handle bold text
    content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', content)
    
    # Handle bullet points
    lines = content.strip().split('\n')
    formatted_lines = []
    in_list = False
    
    for line in lines:
        line = line.strip()
        if line.startswith('- '):
            if not in_list:
                formatted_lines.append('<ul>')
                in_list = True
            formatted_lines.append(f'<li>{line.replace("- ", "")}</li>')
        else:
            if in_list:
                formatted_lines.append('</ul>')
                in_list = False
            if line:
                formatted_lines.append(f'<p>{line}</p>')
    
    if in_list:
        formatted_lines.append('</ul>')
    
    return '\n'.join(formatted_lines)

@app.get("/meal-plan/{analysis_id}")
async def serve_meal_plan_analysis(analysis_id: str):
    """Serve full cart analysis by ID as formatted HTML"""
    try:
        # Import our file utilities
        from file_utils import get_analysis_by_id
        
        # Get the analysis data
        analysis_data = get_analysis_by_id(analysis_id)
        if not analysis_data:
            return HTMLResponse(
                "<h1>Analysis Not Found</h1><p>This meal plan analysis could not be found or may have expired.</p>",
                status_code=404
            )
        
        # Get analysis data
        content = analysis_data.get('content', '')
        created_at = analysis_data.get('created_at', '')
        char_count = analysis_data.get('character_count', 0)
        
        # Parse the content to extract structured information
        # This is more sophisticated than simple markdown conversion
        html_content = parse_analysis_to_html(content)
        
        # Create full HTML page
        html_page = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Farm to People - Cart Analysis</title>
            <style>
                body {{ 
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    line-height: 1.6;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    background-color: #f8f9fa;
                    color: #333;
                }}
                .container {{
                    background: white;
                    padding: 30px;
                    border-radius: 12px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                }}
                h1 {{ 
                    color: #2c5530; 
                    text-align: center;
                    margin-bottom: 30px;
                    font-size: 2.2em;
                }}
                h2 {{ 
                    color: #2c5530; 
                    border-bottom: 2px solid #7bb77b;
                    padding-bottom: 8px;
                    margin-top: 30px;
                }}
                h3 {{ 
                    color: #4a7c59;
                    margin-top: 25px;
                    margin-bottom: 15px;
                }}
                .header {{
                    text-align: center; 
                    margin-bottom: 30px;
                    padding-bottom: 20px;
                    border-bottom: 1px solid #eee;
                }}
                .header p {{
                    color: #666; 
                    margin: 5px 0;
                }}
                .meal-item {{
                    background: #f8fdf8;
                    padding: 15px;
                    margin: 10px 0;
                    border-left: 4px solid #7bb77b;
                    border-radius: 4px;
                }}
                .swap-item {{
                    background: #fff4e6;
                    padding: 15px;
                    margin: 10px 0;
                    border-left: 4px solid #ff9500;
                    border-radius: 4px;
                }}
                .pricing {{
                    background: #e8f5e8;
                    padding: 2px 8px;
                    border-radius: 4px;
                    font-weight: bold;
                    color: #2c5530;
                }}
                .status-complete {{
                    color: #28a745;
                    font-weight: bold;
                }}
                .confirm-buttons {{
                    background: #e8f5e8;
                    padding: 20px;
                    border-radius: 8px;
                    margin-top: 30px;
                    text-align: center;
                }}
                .confirm-buttons p {{
                    margin: 5px 0;
                    font-weight: bold;
                }}
                .footer {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #eee;
                    font-size: 0.9em;
                    color: #666;
                    text-align: center;
                }}
                p {{
                    margin: 12px 0;
                }}
                ul {{
                    padding-left: 20px;
                }}
                li {{
                    margin: 8px 0;
                }}
                strong {{
                    color: #2c5530;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🛒 Your Cart Analysis</h1>
                    <p>Generated by Farm to People AI</p>
                </div>
                
                {html_content}
                
                <div class="confirm-buttons">
                    <p>📱 Ready to get detailed recipes?</p>
                    <p>Reply to our SMS with <strong>CONFIRM</strong> to generate your complete meal plan PDF</p>
                </div>
                
                <div class="footer">
                    <p>Analysis ID: {analysis_id} | Generated: {created_at[:16]} | {char_count:,} characters</p>
                    <p>🌱 <strong>Farm to People</strong> - Fresh ingredients, strategic meal planning</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return HTMLResponse(html_page)
        
    except Exception as e:
        print(f"Error serving meal plan analysis: {e}")
        import traceback
        traceback.print_exc()
        return HTMLResponse(
            "<h1>Error</h1><p>Sorry, there was an error loading your meal plan analysis.</p>",
            status_code=500
        )

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

# ============================================================================
# PREFERENCE ONBOARDING ENDPOINTS
# Research-backed onboarding flow with farm box meal selection
# ============================================================================

@app.get("/")
async def home_page(request: Request):
    """
    Serve the main landing page with links to onboarding and SMS instructions.
    """
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/sms")
async def sms_optin_page(request: Request):
    """
    Serve the SMS opt-in instructions page for Vonage compliance.
    
    This page shows clear Text-to-Join instructions as required by Vonage.
    """
    return templates.TemplateResponse("sms_optin.html", {"request": request})

@app.get("/dashboard")
async def dashboard_page(request: Request):
    """
    Serve the main dashboard after onboarding.
    
    This is where users start cart analysis and view meal plans.
    """
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/api/get-saved-cart")
async def get_saved_cart():
    """Retrieve saved cart data from database"""
    try:
        # Get the user's phone number from session or default test number
        phone_number = "+14254955323"  # Your phone number
        
        # Get saved cart data from database
        saved_cart = db.get_latest_cart_data(phone_number)
        
        if saved_cart and saved_cart.get('cart_data'):
            return {
                "cart_data": saved_cart['cart_data'],
                "delivery_date": saved_cart.get('delivery_date'),
                "scraped_at": saved_cart.get('scraped_at'),
                "swaps": [],  # Can be populated later
                "addons": []  # Can be populated later
            }
        else:
            return {"error": "No saved cart data found"}
            
    except Exception as e:
        print(f"Error retrieving saved cart: {e}")
        return {"error": str(e)}

@app.post("/api/analyze-cart")
async def analyze_cart_api(request: Request, background_tasks: BackgroundTasks):
    """
    API endpoint for cart analysis from the dashboard.
    
    Applying Design of Everyday Things principles:
    - Immediate feedback (returns quickly with status)
    - Visibility of system status (can poll for updates)
    - Error prevention (validates credentials first)
    """
    try:
        data = await request.json()
        
        # Check if we should use mock data or real scraping
        use_mock = data.get('use_mock', False)
        phone = data.get('phone')
        
        cart_data = None
        
        if not use_mock and phone:
            # Try to get real cart data using stored credentials
            try:
                print(f"🔍 Looking up credentials for {phone}")
                
                # Try multiple phone formats like other endpoints do
                phone_formats = [phone, f"+{phone}", f"1{phone}" if not phone.startswith('1') else phone, f"+1{phone}"]
                user_record = None
                
                for phone_format in phone_formats:
                    print(f"  📞 Trying phone format: {phone_format}")
                    user_record = db.get_user_by_phone(phone_format)
                    if user_record:
                        print(f"  ✅ Found user with format: {phone_format}")
                        break
                
                # Get user credentials from database
                if user_record and user_record.get('ftp_email'):
                    email = user_record['ftp_email']
                    # Decrypt password (it's base64 encoded)
                    import base64
                    encoded_pwd = user_record.get('ftp_password_encrypted', '')
                    password = base64.b64decode(encoded_pwd).decode('utf-8') if encoded_pwd else None
                    
                    if email and password:
                        print(f"🛒 Running live scraper for {email}")
                        # Run the actual scraper with return_data=True (properly isolated from async context)
                        credentials = {'email': email, 'password': password}
                        
                        # Use async scraper directly (clean solution)
                        cart_data = await run_cart_scraper(credentials, return_data=True)
                        
                        if cart_data:
                            print("✅ Successfully scraped live cart data!")
                        else:
                            # Return error instead of mock data
                            return {
                                "success": False,
                                "error": "Scraper returned no data. Please check your Farm to People account.",
                                "debug_info": "Scraper ran but returned None"
                            }
                    else:
                        # Return error instead of mock data
                        return {
                            "success": False,
                            "error": "Missing Farm to People credentials. Please log in first.",
                            "debug_info": f"User found but no credentials stored for {email if 'email' in locals() else 'unknown'}"
                        }
                else:
                    # Return error instead of mock data
                    return {
                        "success": False,
                        "error": "User not found. Please complete onboarding first.",
                        "debug_info": f"No user record found for phone: {phone}"
                    }
                    
            except Exception as e:
                # Return error instead of mock data
                print(f"❌ Error scraping cart: {str(e)}")
                return {
                    "success": False,
                    "error": f"Failed to scrape cart: {str(e)}",
                    "debug_info": {
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    }
                }
        
        # Remove all mock data - if we don't have real data, return error
        if not cart_data:
            return {
                "success": False,
                "error": "No cart data available. Please provide credentials or try again.",
                "debug_info": "Cart data is None after all attempts"
            }
        
        # Generate AI-powered swaps and add-ons based on preferences (2025-08-29)
        swaps = []
        addons = []
        
        # Get user preferences if we have phone
        user_preferences = {}
        if phone:
            try:
                phone_formats = [phone, f"+{phone}", f"1{phone}" if not phone.startswith('1') else phone, f"+1{phone}"]
                for phone_format in phone_formats:
                    user_record = db.get_user_by_phone(phone_format)
                    if user_record:
                        user_preferences = user_record.get('preferences', {})
                        break
            except:
                pass
        
        # Use GPT-5 to generate smart swaps and add-ons
        if cart_data and cart_data.get("customizable_boxes"):
            try:
                import openai
                openai_key = os.getenv("OPENAI_API_KEY")
                if openai_key:
                    client = openai.OpenAI(api_key=openai_key)
                    
                    # Build context for GPT-5
                    selected_items = []
                    available_alternatives = []
                    
                    for box in cart_data.get("customizable_boxes", []):
                        selected_items.extend([item["name"] for item in box.get("selected_items", [])])
                        available_alternatives.extend([item["name"] for item in box.get("available_alternatives", [])])
                    
                    # Extract key preferences
                    liked_meals = user_preferences.get('liked_meals', [])
                    cooking_methods = user_preferences.get('cooking_methods', [])
                    dietary_restrictions = user_preferences.get('dietary_restrictions', [])
                    health_goals = user_preferences.get('goals', [])
                    
                    # Get household size for portion calculations
                    household_size = user_preferences.get('household_size', '1-2')
                    servings_needed = 2 if '1-2' in str(household_size) else 4 if '3-4' in str(household_size) else 6
                    
                    prompt = f"""Analyze this Farm to People cart and suggest smart swaps and fresh add-ons.

CURRENT CART:
{', '.join(selected_items)}

AVAILABLE ALTERNATIVES (can swap to these):
{', '.join(available_alternatives)}

USER PREFERENCES:
- Household size: {household_size} (needs {servings_needed} servings per meal)
- Liked meals: {', '.join(liked_meals[:5]) if liked_meals else 'Not specified'}
- Cooking methods: {', '.join(cooking_methods) if cooking_methods else 'Any'}
- Dietary restrictions: {', '.join(dietary_restrictions) if dietary_restrictions else 'None'}
- Health goals: {', '.join(health_goals) if health_goals else 'None'}

IMPORTANT CONTEXT FOR ANALYSIS:
- Portion sizes: 0.6-1lb chicken thighs serves 2 people for ONE meal only
- 1lb sausage serves 3-4 people for one meal
- Don't suggest swapping items that were already swapped
- If making multiple meals, check if there's enough protein (may need to suggest adding more)
- CONSOLIDATION: Consider swapping variety for simplicity
  Example: If they have zucchini and kale, suggest swapping kale for another zucchini
  This gives them 2 units of zucchini instead of 1 each of different vegetables
  Simplifies meal planning with fewer different ingredients
  NOTE: Cannot double up on proteins (portions are fixed per package)

TASK:
1. SWAPS: Suggest 2-3 swaps where an alternative would work better based on:
   - What goes better with other items in cart
   - User's meal preferences (if they like chicken dishes but have pork, suggest swapping)
   - Health goals (if eating healthy, suggest leaner proteins)
   - Recipe compatibility
   - Don't suggest swapping something they likely already chose intentionally

2. ADD-ONS: Suggest 2-3 FRESH ingredients that would complete meals:
   - DO NOT suggest items already in the cart (check CURRENT CART above)
   - Additional protein if there's not enough for multiple meals they want to make
   - Fresh herbs for proteins (basil, cilantro, parsley, etc.)
   - Consider ginger, garlic, fresh peppers for Asian dishes
   - Fresh items that expire (no salt, oil, vinegar)
   - Things that elevate or complete the dishes
   - Be creative - suggest variety, not just lemons every time

Return JSON format (generate appropriate suggestions based on cart):
{{
  "swaps": [
    {{"from": "item name", "to": "alternative name", "reason": "specific reason"}}
  ],
  "addons": [
    {{"item": "Fresh item name", "price": "$X.XX", "reason": "how it enhances their meals", "category": "produce/protein/dairy"}}
  ]
}}

IMPORTANT: Each addon MUST have a category field with one of these values:
- "protein" (meats, fish, eggs)
- "produce" (vegetables, fruits, herbs)
- "dairy" (cheese, milk, yogurt)
- "pantry" (oils, spices - but avoid these per instructions)
"""

                    response = client.chat.completions.create(
                        model=AI_MODEL,
                        messages=[
                            {"role": "system", "content": "You are a Farm to People meal planning expert. Analyze carts and suggest smart improvements based on user preferences."},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=500,
                        temperature=0.7
                    )
                    
                    # Parse response
                    import json
                    import re
                    gpt_response = response.choices[0].message.content.strip()
                    json_match = re.search(r'\{.*\}', gpt_response, re.DOTALL)
                    if json_match:
                        result = json.loads(json_match.group())
                        swaps = result.get("swaps", [])
                        addons = result.get("addons", [])
                        print(f"✅ Generated {len(swaps)} swaps and {len(addons)} add-ons via GPT-5")
                    
            except Exception as e:
                print(f"⚠️ Could not generate AI swaps: {e}")
                # Return empty swaps/addons rather than hardcoded ones
                pass
        
        return {"success": True, "cart_data": cart_data, "swaps": swaps, "addons": addons}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/refresh-meals")
async def refresh_meal_suggestions(request: Request):
    """
    Generate new meal suggestions from the same cart data.
    
    This allows users to get different meal ideas without re-analyzing their cart.
    Limited to prevent abuse (track refresh count on frontend).
    """
    try:
        data = await request.json()
        cart_data = data.get('cart_data')
        phone = data.get('phone')
        
        if not cart_data:
            return {"success": False, "error": "No cart data provided"}
        
        # Get user preferences for personalized meal generation
        user_preferences = {}
        if phone:
            try:
                # Try multiple phone formats like other endpoints do
                phone_formats = [phone, f"+{phone}", f"1{phone}" if not phone.startswith('1') else phone, f"+1{phone}"]
                user_record = None
                
                for phone_format in phone_formats:
                    user_record = db.get_user_by_phone(phone_format)
                    if user_record:
                        break
                
                if user_record:
                    user_preferences = user_record.get('preferences', {})
            except Exception as e:
                print(f"⚠️ Could not load user preferences: {e}")
        
        # Generate meals using ONLY ingredients actually in the cart
        try:
            print(f"🍽️ STEP 1: Analyzing cart contents for meal generation...")
            
            # Extract all actual ingredients from cart
            proteins = []
            vegetables = []
            other_items = []
            
            # Individual items
            for item in cart_data.get('individual_items', []):
                name = item.get('name', '').lower()
                if 'egg' in name:
                    proteins.append('eggs')
                elif 'avocado' in name:
                    other_items.append('avocados')
                elif 'banana' in name:
                    other_items.append('bananas')
                else:
                    other_items.append(item.get('name', ''))
            
            # Customizable boxes (your actual selected items)
            for box in cart_data.get('customizable_boxes', []):
                for item in box.get('selected_items', []):
                    name = item.get('name', '').lower()
                    if any(meat in name for meat in ['chicken', 'beef', 'turkey', 'sausage', 'fish', 'pork']):
                        proteins.append(item.get('name', ''))
                    elif any(veg in name for veg in ['tomato', 'pepper', 'kale', 'lettuce', 'carrot', 'zucchini', 'eggplant', 'onion']):
                        vegetables.append(item.get('name', ''))
                    else:
                        other_items.append(item.get('name', ''))
            
            # Non-customizable boxes
            for box in cart_data.get('non_customizable_boxes', []):
                for item in box.get('selected_items', []):
                    name = item.get('name', '').lower()
                    if any(fruit in name for fruit in ['plum', 'peach', 'nectarine', 'apple']):
                        other_items.append(item.get('name', ''))
                    else:
                        other_items.append(item.get('name', ''))
            
            # Report what was found in cart
            total_ingredients = len(proteins) + len(vegetables) + len(other_items)
            print(f"📊 STEP 2: Cart analysis complete!")
            print(f"  ✅ Found {len(proteins)} proteins: {proteins}")
            print(f"  ✅ Found {len(vegetables)} vegetables: {vegetables}")  
            print(f"  ✅ Found {len(other_items)} other items: {other_items}")
            print(f"  📈 Total ingredients available: {total_ingredients}")
            
            # Use GPT-5 to create creative meal suggestions from actual ingredients
            all_ingredients = proteins + vegetables + other_items
            ingredients_text = ", ".join(all_ingredients)
            
            print(f"🤖 STEP 3: Sending ingredient list to GPT-5 for creative meal ideas...")
            
            # Extract ALL preferences for meal planning
            household_size = user_preferences.get('household_size', '2 people')
            meal_focus = user_preferences.get('meal_timing', ['dinner'])
            dietary_restrictions = user_preferences.get('dietary_restrictions', [])
            health_goals = user_preferences.get('goals', [])
            cooking_time = 'quick (under 30 min)' if 'quick-dinners' in health_goals else 'standard'
            high_protein = 'high-protein' in health_goals
            
            # Additional preferences we should be using
            cooking_methods = user_preferences.get('cooking_methods', user_preferences.get('preferred_cooking_methods', []))
            liked_meals = user_preferences.get('liked_meals', [])
            dislikes = user_preferences.get('dislikes', [])
            # Note: We don't capture skill level yet - default to intermediate
            skill_level = 'intermediate'  # TODO: Add skill level to onboarding
            
            # Calculate servings needed based on household size
            servings_per_meal = 2 if '1-2' in str(household_size) else 4 if '3-4' in str(household_size) else 6
            
            print(f"  👥 Household size: {household_size} ({servings_per_meal} servings per meal)")
            print(f"  🍽️ Meal focus: {meal_focus}")
            print(f"  🚫 Dietary restrictions: {dietary_restrictions}")
            print(f"  ❌ Dislikes: {dislikes if dislikes else 'None'}")
            print(f"  🎯 Health goals: {health_goals}")
            print(f"  👨‍🍳 Cooking methods: {cooking_methods if cooking_methods else 'Any'}")
            print(f"  ❤️ Liked meals: {liked_meals[:3] if liked_meals else 'Not specified'}")
            
            # Build focused prompt for GPT-5 WITH PREFERENCES
            prompt = f"""Analyze this cart and create meal suggestions for a household of {household_size}.

CART CONTENTS:
PROTEINS ({len(proteins)} items): {', '.join(proteins) if proteins else 'none'}
VEGETABLES ({len(vegetables)} items): {', '.join(vegetables) if vegetables else 'none'}  
OTHER ITEMS ({len(other_items)} items): {', '.join(other_items) if other_items else 'none'}

USER PREFERENCES:
- Household size: {household_size} (need {servings_per_meal} servings per meal)
- Meal focus: Primarily {', '.join(meal_focus) if isinstance(meal_focus, list) else meal_focus}
- Dietary restrictions: {', '.join(dietary_restrictions) if dietary_restrictions else 'None'}
- Foods to avoid: {', '.join(dislikes) if dislikes else 'None'}
- Cooking time preference: {cooking_time}
- Protein requirement: {'HIGH (35-40g per serving)' if high_protein else 'Standard (25-30g per serving)'}
- Preferred cooking methods: {', '.join(cooking_methods) if cooking_methods else 'Any'}
- Meals they enjoy: {', '.join(liked_meals[:5]) if liked_meals else 'Not specified'}

CRITICAL ANALYSIS REQUIRED:
1. Calculate REALISTICALLY how many complete {meal_focus[0] if isinstance(meal_focus, list) else 'dinner'}s this cart can make for {household_size}
2. Protein portion reality check:
   - 0.6-1lb chicken thighs = ONE meal for 2 people (not multiple meals)
   - 1lb sausage = ONE meal for 3-4 people
   - 1 dozen eggs = 2-3 breakfast/brunch meals for 2 people
   - Don't overcount - be honest about portions
3. If suggesting multiple meals with same protein, note that they'd need to buy more
4. Create meal names that reflect the actual ingredients (not generic names)
5. Be clear: "Makes 1 dinner" vs "Makes 2 dinners" based on actual portions

Return 4 meal suggestions focusing on {meal_focus[0] if isinstance(meal_focus, list) else 'dinner'} meals.

STYLE YOUR SUGGESTIONS BASED ON PREFERENCES:
{"- Match their preferred cooking methods: " + ', '.join(cooking_methods) if cooking_methods else ""}
{"- Similar to meals they enjoy: " + ', '.join(liked_meals[:3]) if liked_meals else ""}
{"- AVOID any ingredients containing: " + ', '.join(dislikes) if dislikes else ""}
{"- IMPORTANT: Do NOT suggest breakfast items if user prefers dinner!" if 'dinner' in str(meal_focus) else ""}
{"- All meals MUST be high-protein (35g+ per serving)" if high_protein else ""}
{"- All meals MUST be quick (under 30 minutes total time)" if cooking_time == 'quick (under 30 min)' else ""}

Format as JSON:
[{{
  "name": "Specific Meal Name Using Actual Ingredients",
  "servings": {servings_per_meal},
  "time": "X min",
  "protein_per_serving": X,
  "makes_x_dinners": "This recipe makes X dinners for your family",
  "ingredients_used": ["list", "actual", "cart", "items", "used"],
  "note": "optional note about what to add from store"
}}]"""

            try:
                import openai
                
                # Check if we have OpenAI client
                openai_key = os.getenv("OPENAI_API_KEY")
                if not openai_key:
                    raise Exception("No OpenAI API key")
                
                client = openai.OpenAI(api_key=openai_key)
                print(f"  🔗 Connected to OpenAI API")
                print(f"  🧠 Using {AI_MODEL} model for meal creativity")
                
                response = client.chat.completions.create(
                    model=AI_MODEL,  # Use configured model for meal suggestions
                    messages=[
                        {"role": "system", "content": "You are a creative chef who specializes in making delicious meals from specific available ingredients. Always return valid JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=800,
                    temperature=0.7
                )
                
                # Parse GPT response
                gpt_response = response.choices[0].message.content.strip()
                print(f"✅ STEP 4: GPT-5 responded successfully!")
                print(f"📝 GPT Response: {gpt_response[:200]}{'...' if len(gpt_response) > 200 else ''}")  # Truncate long responses
                
                # Try to extract JSON from response
                import json
                import re
                
                print(f"🔍 STEP 5: Parsing GPT response for meal suggestions...")
                
                # Look for JSON array in the response
                json_match = re.search(r'\[.*\]', gpt_response, re.DOTALL)
                if json_match:
                    meals_json = json.loads(json_match.group())
                    print(f"  ✅ Successfully parsed JSON from GPT response")
                    
                    # Validate and format the meals with enhanced preference data
                    meals = []
                    for meal in meals_json[:4]:  # Limit to 4
                        if isinstance(meal, dict) and 'name' in meal:
                            meals.append({
                                "name": meal.get('name', 'Unknown Meal'),
                                "time": meal.get('time', '25 min'),
                                "protein": meal.get('protein_per_serving', meal.get('protein', 25)),
                                "servings": meal.get('servings', servings_per_meal),
                                "makes_x_dinners": meal.get('makes_x_dinners', f"Makes 1 meal for {household_size}"),
                                "ingredients_used": meal.get('ingredients_used', []),
                                "note": meal.get('note', ''),
                                "type": "dinner" if 'dinner' in str(meal_focus) else "lunch" if 'lunch' in str(meal_focus) else "breakfast"
                            })
                    
                    if meals:
                        print(f"🎉 SUCCESS: Created {len(meals)} personalized meal suggestions!")
                        for i, meal in enumerate(meals, 1):
                            print(f"  {i}. {meal['name']} ({meal['time']}, {meal['protein']}g protein)")
                            print(f"     → {meal['makes_x_dinners']}")
                            if meal.get('ingredients_used'):
                                print(f"     → Uses: {', '.join(meal['ingredients_used'][:3])}")
                        
                        # Save meal suggestions to database for meal calendar consistency
                        if phone:
                            try:
                                # Convert meals to storage format
                                meal_suggestions = []
                                for meal in meals:
                                    meal_data = {
                                        'title': meal['name'],
                                        'protein': str(meal.get('protein', 25)),
                                        'cook_time': meal.get('time', '30 min'),
                                        'servings': meal.get('servings', servings_per_meal),
                                        'ingredients': meal.get('ingredients_used', []),
                                        'instructions': [],  # Will be filled when detailed recipes are generated
                                        'nutrition': {'protein_g': meal.get('protein', 25)},
                                        'makes_x_dinners': meal.get('makes_x_dinners', '')
                                    }
                                    meal_suggestions.append(meal_data)
                                
                                # Save to database
                                db.save_latest_cart_data(
                                    phone_number=phone,
                                    cart_data=cart_data,
                                    meal_suggestions=meal_suggestions
                                )
                                print(f"✅ Saved {len(meal_suggestions)} meal suggestions to database for calendar")
                            except Exception as e:
                                print(f"⚠️ Failed to save meal suggestions to database: {e}")
                                # Continue even if saving fails
                        
                        return {"success": True, "meals": meals, "household_size": household_size}
                
                print(f"⚠️ Could not extract valid JSON from GPT response")
                
            except Exception as e:
                print(f"❌ STEP 4 FAILED: GPT meal generation error: {e}")
                print(f"🔍 Error type: {type(e).__name__}")
                print(f"📝 Full error details: {str(e)}")
                print(f"🔄 Meal generation failed - returning error status")
            
            # Updated 2025-08-29: Return error instead of fake fallback meals
            # Previously returned hardcoded meals which was misleading - now shows clear error
            return {
                "success": False, 
                "error": f"Unable to generate meal suggestions. {AI_MODEL} failed to respond.",
                "meals": [],
                "debug_info": {
                    "proteins_found": proteins,
                    "vegetables_found": vegetables,
                    "other_items_found": other_items,
                    "error_message": str(e) if 'e' in locals() else "Unknown error"
                }
            }
                
        except Exception as e:
            print(f"❌ Error generating cart-based meals: {e}")
            return {
                "success": False,
                "error": f"Critical error in meal generation: {str(e)}",
                "meals": []
            }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/onboard")
async def serve_onboarding(request: Request, phone: str = None):
    """
    Serve the tile-based preference onboarding flow.
    
    This implements research-backed UX patterns:
    - <2 minute completion time
    - Progressive disclosure (70/30 familiar/adventurous meals)
    - Clear selection states with visual feedback
    - Skip options to reduce friction
    - 4-step flow: Household → Meals → Restrictions → Goals
    """
    return templates.TemplateResponse("onboarding.html", {
        "request": request,
        "phone": phone
    })

@app.post("/api/onboarding")
async def save_onboarding_preferences(request: Request):
    """
    Save user preferences from onboarding flow.
    
    This delegates to the onboarding module to keep server.py lean.
    """
    import onboarding
    data = await request.json()
    return await onboarding.save_preferences(data)

# Settings Page Routes
@app.get("/settings")
async def serve_settings_page(request: Request):
    """
    Serve the settings page for updating user preferences.
    
    Shows 5 clickable categories that allow users to update preferences
    collected during onboarding: household size, meal timing, cooking style,
    dietary restrictions, and health goals.
    """
    return templates.TemplateResponse("settings.html", {
        "request": request
    })


@app.get("/api/settings/options")
async def get_settings_options():
    """
    Get available options for all settings categories.
    
    Returns the same option lists used in onboarding to ensure consistency
    in the settings modal forms. This includes household sizes, meal timings,
    dietary restrictions, goals, and cooking methods.
    
    Returns:
        JSON with all available options for each category
    """
    try:
        # Import the preference options from onboarding models
        # These should match exactly what's available in onboarding
        options = {
            "household_sizes": ["1-2", "3-4", "5-6", "7+"],
            "meal_timings": [
                {"id": "breakfast", "label": "Breakfast", "icon": "🌅"},
                {"id": "lunch", "label": "Lunch", "icon": "☀️"},
                {"id": "dinner", "label": "Dinner", "icon": "🌙"},
                {"id": "snacks", "label": "Snacks", "icon": "🥨"}
            ],
            "dietary_restrictions": [
                {"id": "high-protein", "label": "High Protein (30g+ per meal)"},
                {"id": "vegetarian", "label": "Vegetarian (no meat or fish)"},
                {"id": "no-pork", "label": "No Pork (halal/kosher friendly)"},
                {"id": "dairy-free", "label": "Dairy-Free"},
                {"id": "gluten-free", "label": "Gluten-Free"},
                {"id": "low-carb", "label": "Low-Carb"},
                {"id": "nut-free", "label": "Nut-Free"},
                {"id": "no-shellfish", "label": "No Shellfish"},
                {"id": "mediterranean", "label": "Mediterranean Diet"},
                {"id": "keto", "label": "Keto Diet"},
                {"id": "paleo", "label": "Paleo Diet"}
            ],
            "goals": [
                {"id": "quick-dinners", "label": "Quick Dinners (20 min or less)", "icon": "⚡"},
                {"id": "whole-food", "label": "Whole Food Focus", "icon": "🥬"},
                {"id": "new-recipes", "label": "Try New Recipes", "icon": "✨"},
                {"id": "reduce-waste", "label": "Reduce Food Waste", "icon": "♻️"},
                {"id": "family-friendly", "label": "Family-Friendly Meals", "icon": "👨‍👩‍👧‍👦"},
                {"id": "meal-prep", "label": "Great for Meal Prep", "icon": "📦"}
            ],
            "cooking_methods": [
                {"id": "roast", "label": "Roasting & Baking"},
                {"id": "stir_fry", "label": "Stir-Fry & Sauté"},
                {"id": "grill_pan", "label": "Grilling & Pan-Searing"},
                {"id": "one_pot", "label": "One-Pot Meals"},
                {"id": "raw_prep", "label": "Fresh & Raw (Salads, Bowls)"},
                {"id": "slow_cook", "label": "Slow Cooking & Braising"}
            ]
        }
        
        return {"success": True, "options": options}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/settings/{phone}")
async def get_user_preferences(phone: str):
    """
    Fetch user preferences by phone number for settings display.
    
    Returns structured preference data to populate the settings preview cards
    and modal forms. Phone number should be URL-encoded if it contains special characters.
    
    Args:
        phone: User's phone number (with or without +1 prefix)
    
    Returns:
        JSON with preference categories or error if user not found
    """
    try:
        # Try multiple phone number formats to find user
        phone_formats = []
        
        # Add original format
        phone_formats.append(phone)
        
        # Add normalized format (with +1)
        if not phone.startswith('+'):
            phone_formats.append('+1' + phone.lstrip('+1'))
        
        # Add without +1 prefix
        if phone.startswith('+1'):
            phone_formats.append(phone[2:])
        
        # Add with 1 prefix but no +
        if not phone.startswith('1') and not phone.startswith('+'):
            phone_formats.append('1' + phone)
            
        print(f"🔍 Looking up user preferences for phone formats: {phone_formats}")
        
        # Try each format until we find the user
        user_record = None
        for phone_format in phone_formats:
            user_record = db.get_user_by_phone(phone_format)
            if user_record:
                print(f"  ✅ Found user with format: {phone_format}")
                break
        
        if not user_record:
            print("  ❌ User not found with any phone format")
            return {"success": False, "error": "User not found"}
        
        preferences = user_record.get('preferences', {})
        
        # Structure preferences for settings UI
        settings_data = {
            "household_size": preferences.get('household_size', '1-2'),
            "meal_timing": preferences.get('meal_timing', []),
            "dietary_restrictions": preferences.get('dietary_restrictions', []),
            "goals": preferences.get('goals', []),
            # Extract cooking style from derived preferences (try multiple keys)
            "cooking_methods": preferences.get('preferred_cooking_methods', preferences.get('cooking_methods', [])),
            "time_preferences": preferences.get('time_preferences', [])
        }
        
        # Include FTP credentials for onboarding existing user detection
        response_data = {
            "success": True, 
            "preferences": settings_data,
            "ftp_email": user_record.get('ftp_email'),
            "ftp_password_encrypted": user_record.get('ftp_password_encrypted')
        }
        
        return response_data
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/settings/{phone}/update")
async def update_user_preferences(phone: str, request: Request):
    """
    Update specific preference categories for a user.
    
    Accepts partial updates to allow updating individual categories
    without affecting others. This enables the modal-based editing flow
    where each category can be updated independently.
    
    Args:
        phone: User's phone number
        request body: JSON with category updates, e.g.:
            {
                "category": "household",
                "value": "3-4"
            }
            OR
            {
                "category": "dietary", 
                "value": ["high-protein", "no-pork"]
            }
    
    Returns:
        Success/error status and updated preference summary
    """
    try:
        # Log incoming request for debugging
        data = await request.json()
        print(f"📝 Settings update request for phone: {phone}")
        print(f"   Category: {data.get('category')}")
        print(f"   Value: {data.get('value')}")
        
        # Try multiple phone formats to find user
        phone_formats = [phone]
        if not phone.startswith('+'):
            phone_formats.append('+1' + phone.lstrip('+1'))
        if phone.startswith('+1'):
            phone_formats.append(phone[2:])
        if not phone.startswith('1') and not phone.startswith('+'):
            phone_formats.append('1' + phone)
        
        category = data.get('category')
        value = data.get('value')
        
        if not category or value is None:
            return {"success": False, "error": "Missing category or value"}
        
        # Try each format to find user
        user_record = None
        for phone_format in phone_formats:
            user_record = db.get_user_by_phone(phone_format)
            if user_record:
                phone = phone_format  # Use the format that worked
                print(f"✅ Found user with phone format: {phone_format}")
                break
        
        if not user_record:
            print(f"❌ User not found with any phone format: {phone_formats}")
            return {"success": False, "error": "User not found"}
        
        # Get current preferences
        current_preferences = user_record.get('preferences', {})
        
        # Update the specific category
        if category == "household":
            current_preferences['household_size'] = value
        elif category == "meals":
            current_preferences['meal_timing'] = value
        elif category == "dietary":
            current_preferences['dietary_restrictions'] = value
        elif category == "goals":
            current_preferences['goals'] = value
        elif category == "cooking":
            # Handle cooking style updates (methods and time preferences)
            if isinstance(value, dict):
                current_preferences['preferred_cooking_methods'] = value.get('methods', [])
                current_preferences['time_preferences'] = value.get('time', [])
            else:
                return {"success": False, "error": "Cooking preferences must be an object with 'methods' and 'time' arrays"}
        else:
            return {"success": False, "error": f"Unknown category: {category}"}
        
        # Update the database record
        # Note: We need to handle the password properly - it's already encrypted
        try:
            # If password is encrypted (base64), decode it for the upsert function
            import base64
            encrypted_pwd = user_record.get('ftp_password_encrypted', '')
            if encrypted_pwd:
                # The upsert function expects plain password and encrypts it
                plain_password = base64.b64decode(encrypted_pwd).decode('utf-8')
            else:
                plain_password = ''
            
            updated_record = db.upsert_user_credentials(
                phone_number=phone,
                ftp_email=user_record.get('ftp_email', ''),
                ftp_password=plain_password,  # Pass plain password - upsert will encrypt it
                preferences=current_preferences
            )
            print(f"✅ Successfully updated preferences for {phone}")
        except Exception as e:
            print(f"❌ Database update error: {e}")
            raise
        
        return {"success": True, "message": "Preferences updated successfully"}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    import os
    # To run this server locally, use the command:
    # uvicorn server:app --reload
    port = int(os.getenv("PORT", 8000))
    print(f"Starting server on port {port}... To test locally, run 'uvicorn server:app --reload' in your terminal.")
    # This part is for local development and won't be used in production
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)
