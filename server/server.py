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


app = FastAPI()

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

def run_full_meal_plan_flow(phone_number: str):
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
                            print("⚠️ Scraper returned no data, falling back to mock")
                    else:
                        print("⚠️ Missing credentials, using mock data")
                else:
                    print("⚠️ User not found, using mock data")
                    
            except Exception as e:
                print(f"❌ Error scraping cart: {str(e)}")
                print("⚠️ Falling back to mock data")
        
        # If we don't have real data yet, use mock
        if not cart_data:
            print("🧪 Using mock cart data")
            cart_data = {
            "individual_items": [
                {"name": "Pasture Raised Eggs", "quantity": 1, "unit": "1 dozen", "price": "$7.49", "type": "individual"},
                {"name": "Organic & Fair Trade Hass Avocados", "quantity": 5, "unit": "1 piece", "price": "$8.00", "type": "individual"},
                {"name": "Organic & Fair Trade Bananas (Ripe)", "quantity": 1, "unit": "1 bunch", "price": "$2.49", "type": "individual"}
            ],
            "customizable_boxes": [
                {
                    "box_name": "The Cook's Box - Paleo",
                    "selected_items": [
                        {"name": "Boneless, Skinless Chicken Breast", "unit": ".7-1lb", "producer": "Locust Point Farm"},
                        {"name": "Black Sea Bass", "unit": "8.0 oz", "producer": "Red's Best Seafood"},
                        {"name": "Local Yellow Peaches", "unit": "2 pieces", "producer": "Lancaster Farm Fresh Cooperative"},
                        {"name": "Organic Leaf Lettuce", "unit": "1 head", "producer": "Sun Sprout Farm"},
                        {"name": "Mixed Cherry Tomatoes", "unit": "1 pint", "producer": "Eagle Road Farm"},
                        {"name": "Lunchbox Peppers", "unit": "12.0 oz", "producer": "Sunny Harvest"},
                        {"name": "Organic Italian Eggplant", "unit": "1 piece", "producer": "Lancaster Farm Fresh Cooperative"},
                        {"name": "Unagi Cucumbers", "unit": "2 pieces", "producer": "Sunny Harvest"},
                        {"name": "Organic Green Zucchini", "unit": "2 pieces", "producer": "Sun Sprout Farm"}
                    ],
                    "available_alternatives": [
                        {"name": "White Ground Turkey", "unit": "1.0 Lbs", "producer": "Koch's Turkey Farm"},
                        {"name": "Pork Kielbasa", "unit": "1 Lbs", "producer": "Autumn's Harvest"},
                        {"name": "Yellow Nectarines", "unit": "2 pieces", "producer": "Weaver's Orchard"},
                        {"name": "Red Onions", "unit": "2 Lbs", "producer": "Dagele Brothers Produce"},
                        {"name": "Yellow Onions", "unit": "2.0 Lbs", "producer": "Dagele Brothers Produce"}
                    ],
                    "selected_count": 9,
                    "alternatives_count": 10
                }
            ],
            "non_customizable_boxes": [
                {
                    "box_name": "Seasonal Fruit Medley",
                    "selected_items": [
                        {"name": "Prune Plums", "unit": "1 Lbs"},
                        {"name": "Honeycrisp Apples", "unit": "2 pieces"},
                        {"name": "Local Yellow Peaches", "unit": "2 pieces"}
                    ],
                    "selected_count": 3,
                    "customizable": False
                }
            ]
        }
        
        return {"success": True, "cart_data": cart_data}
        
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
        
        # TODO: Eventually use meal_planner.generate_from_cart(cart_data)
        # For now, return mock meal suggestions
        mock_meals = [
            {"name": "Mediterranean Chicken Bowl", "time": "25 min", "protein": 35},
            {"name": "Veggie Stir-Fry with Tofu", "time": "20 min", "protein": 18},
            {"name": "Grilled Fish Tacos", "time": "30 min", "protein": 28},
            {"name": "Egg & Vegetable Frittata", "time": "35 min", "protein": 24},
            {"name": "Quinoa Power Bowl", "time": "25 min", "protein": 22}
        ]
        
        # Shuffle to simulate different suggestions
        import random
        random.shuffle(mock_meals)
        
        return {"success": True, "meals": mock_meals[:4]}
        
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
                {"id": "no-shellfish", "label": "No Shellfish"}
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
        # Normalize phone number
        if not phone.startswith('+'):
            phone = '+1' + phone.lstrip('+1')
        
        data = await request.json()
        category = data.get('category')
        value = data.get('value')
        
        if not category or value is None:
            return {"success": False, "error": "Missing category or value"}
        
        # Fetch current user record
        user_record = db.get_user_by_phone(phone)
        if not user_record:
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
        updated_record = db.upsert_user_credentials(
            phone_number=phone,
            ftp_email=user_record['ftp_email'],
            ftp_password=user_record.get('ftp_password_encrypted', ''),  # Keep encrypted password as-is
            preferences=current_preferences
        )
        
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
