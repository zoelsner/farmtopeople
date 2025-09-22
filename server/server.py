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

# Fix import paths for services
current_dir = os.path.dirname(__file__)
sys.path.insert(0, current_dir)  # For server directory imports
sys.path.insert(0, os.path.join(current_dir, 'services'))  # For services imports
sys.path.append(os.path.join(current_dir, '..'))  # For scrapers

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
# Updated 2025-09-15: Support both GPT-4o and GPT-5 via environment variable
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o")  # Default to gpt-4o for stability
print(f"🤖 AI Model configured: {AI_MODEL}")

# Function to determine if model needs max_completion_tokens
def uses_completion_tokens_param(model_name):
    """
    Determine if the model uses max_completion_tokens instead of max_tokens.
    GPT-5 and reasoning models (o1, o3) use max_completion_tokens.
    """
    model_lower = model_name.lower()
    return (
        model_lower.startswith("gpt-5") or
        model_lower.startswith("o1") or
        model_lower.startswith("o3")
    )


def build_api_params(model_name, max_tokens_value, temperature_value=None):
    """
    Build OpenAI API parameters based on model capabilities.

    Args:
        model_name: The OpenAI model name
        max_tokens_value: Maximum tokens to generate
        temperature_value: Temperature setting (None means use model default)

    Returns:
        Dict with appropriate parameters for the model
    """
    params = {}

    # Handle token parameter naming
    if uses_completion_tokens_param(model_name):
        params["max_completion_tokens"] = max_tokens_value
        print(f"📝 [MODEL COMPAT] Using max_completion_tokens for {model_name}")
    else:
        params["max_tokens"] = max_tokens_value
        print(f"📝 [MODEL COMPAT] Using max_tokens for {model_name}")

    # Handle temperature (GPT-5 only supports default temperature=1)
    model_lower = model_name.lower()
    if model_lower.startswith("gpt-5"):
        # GPT-5 only supports temperature=1 (default), so don't specify it
        print(f"📝 [MODEL COMPAT] Skipping temperature for {model_name} (uses default)")

        # GPT-5 REQUIRES reasoning_effort parameter
        params["reasoning_effort"] = "minimal"  # Use minimal for JSON generation tasks
        print(f"📝 [MODEL COMPAT] Using reasoning_effort=minimal for {model_name}")
    elif temperature_value is not None:
        params["temperature"] = temperature_value
        print(f"📝 [MODEL COMPAT] Using temperature={temperature_value} for {model_name}")

    return params

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

# Moved to services/sms_handler.py
from services.sms_handler import format_sms_with_help

def format_sms_with_help_deprecated(message: str, state: str = None) -> str:
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
    Delegates to the meal_flow_service for the complete flow.
    This function used to be 200+ lines, now it's a simple delegation.
    """
    from services.meal_flow_service import run_full_meal_plan_flow as run_flow
    await run_flow(phone_number)


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

    # --- Use SMS Handler Service for Routing ---
    from services.sms_handler import route_sms_message
    base_url = str(request.base_url).rstrip('/')

    # Check if user is in meal plan confirmation flow (keeping this special case for now)
    try:
        user_data = db.get_user_by_phone(user_phone_number)
        if user_data and user_data.get('meal_plan_step') == 'awaiting_confirmation':
            # Handle meal plan confirmation responses
            return await handle_meal_plan_confirmation(user_phone_number, user_message, background_tasks)
    except Exception as e:
        print(f"⚠️ Error checking meal plan step: {e}")

    # Route the message using our service
    reply, should_trigger_task = route_sms_message(user_phone_number, user_message)
    
    # If we need to trigger background meal generation
    if should_trigger_task:
        # Add the scraping/planning job to the background
        print(f"🎯 Adding background task for meal plan flow: {user_phone_number}")
        try:
            background_tasks.add_task(run_full_meal_plan_flow, user_phone_number)
            print(f"✅ Background task added successfully")
        except Exception as e:
            print(f"❌ Error adding background task: {e}")
            # Update reply if task failed
            from services.sms_handler import format_sms_with_help
            reply = format_sms_with_help(
                "We're experiencing a technical issue. Please try again in a moment.", 
                'error'
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

@app.get("/test")
async def test_page(request: Request):
    """
    Serve the meal integration test page.
    """
    return templates.TemplateResponse("test_meal_integration.html", {"request": request})

@app.get("/dashboard-modular")
async def dashboard_modular_page(request: Request):
    """
    Serve the new modular dashboard (cleaner architecture).
    
    This version splits functionality into separate JS modules for better maintainability.
    """
    return templates.TemplateResponse("dashboard-modular.html", {"request": request})

@app.get("/dashboard-v2")
async def dashboard_v2_page(request: Request):
    """
    Serve the fixed modular dashboard that maintains all functionality.

    This version keeps all features but in a more organized structure.
    """
    return templates.TemplateResponse("dashboard-modular-fixed.html", {"request": request})

@app.get("/dashboard-v3")
async def dashboard_v3_page(request: Request):
    """
    Serve the new dashboard v3 with complete modularization and PWA fixes.

    Key improvements:
    - Settings uses modals (no page refresh!)
    - Event-driven architecture with AppState
    - 3546 lines → ~2000 lines across 8 modules
    - Smooth tab transitions
    """
    return templates.TemplateResponse("dashboard-v3.html", {"request": request})

@app.get("/api/get-saved-cart")
async def get_saved_cart(force_refresh: bool = False):
    """Retrieve saved cart data - check Redis first, then database"""
    try:
        # Get the user's phone number from session or default test number
        phone_number = "+14254955323"  # Your phone number

        # CRITICAL: Check Redis cache first for fresh data (unless force_refresh)
        if not force_refresh:
            try:
                from services.cache_service import CacheService

                # First, try to get complete cart response (includes swaps & addons)
                cached_response = CacheService.get_cart_response(phone_number)
                if cached_response:
                    # Validate the cached response before serving it
                    cart_data = cached_response.get('cart_data')
                    if cart_data:
                        has_valid_items = False

                        # Check customizable boxes
                        customizable_boxes = cart_data.get('customizable_boxes', [])
                        for box in customizable_boxes:
                            selected_items = box.get('selected_items', [])
                            if selected_items and len(selected_items) > 0:
                                has_valid_items = True
                                break

                        # Check individual items if no customizable box items found
                        if not has_valid_items:
                            individual_items = cart_data.get('individual_items', [])
                            if individual_items and len(individual_items) > 0:
                                has_valid_items = True

                        # Check non-customizable boxes if still no items found
                        if not has_valid_items:
                            non_customizable_boxes = cart_data.get('non_customizable_boxes', [])
                            for box in non_customizable_boxes:
                                selected_items = box.get('selected_items', [])
                                if selected_items and len(selected_items) > 0:
                                    has_valid_items = True
                                    break

                        if has_valid_items:
                            # Get cached meals if not already in response
                            if "meals" not in cached_response or not cached_response["meals"]:
                                cached_meals = CacheService.get_meals(phone_number)
                                if cached_meals:
                                    cached_response["meals"] = cached_meals
                                    print(f"⚡ Added {len(cached_meals)} cached meals to complete response")

                            print(f"⚡ Serving COMPLETE cart response from Redis cache for {phone_number}")
                            # Add cache metadata
                            cached_response["from_cache"] = True
                            cached_response["cache_type"] = "redis_complete"
                            return cached_response
                        else:
                            print(f"⚠️ Cached response has invalid cart_data (empty selected_items) - invalidating")
                            # Invalidate bad cache entry
                            CacheService.invalidate_cart_response(phone_number)
                    else:
                        print(f"⚠️ Cached response missing cart_data - invalidating")
                        CacheService.invalidate_cart_response(phone_number)

                # Fall back to cart-only cache if complete response not available
                cached_cart = CacheService.get_cart(phone_number)
                if cached_cart:
                    # Also get cached meals for cart-only fallback
                    cached_meals = CacheService.get_meals(phone_number)
                    meals_msg = f" with {len(cached_meals)} meals" if cached_meals else " (no cached meals)"

                    # Try to get cached swaps and addons from last successful scrape
                    cached_response = CacheService.get_cart_response(phone_number)
                    cached_swaps = []
                    cached_addons = []

                    if cached_response:
                        cached_swaps = cached_response.get('swaps', [])
                        cached_addons = cached_response.get('addons', [])
                        swaps_msg = f" with {len(cached_swaps)} swaps" if cached_swaps else ""
                        addons_msg = f" and {len(cached_addons)} add-ons" if cached_addons else ""
                        print(f"✅ Found cached swaps/addons{swaps_msg}{addons_msg}")

                    print(f"⚡ Serving cart-only from Redis cache for {phone_number}{meals_msg}")
                    return {
                        "cart_data": cached_cart,
                        "delivery_date": cached_cart.get('delivery_date'),  # Get delivery date from cart data
                        "scraped_at": cached_cart.get('scraped_timestamp', "cached"),
                        "from_cache": True,
                        "cache_type": "redis_cart_fallback",
                        "swaps": cached_swaps,  # Include cached swaps from last successful scrape
                        "addons": cached_addons,  # Include cached addons from last successful scrape
                        "meals": cached_meals or []  # Ensure meals is always an array
                    }
            except Exception as cache_error:
                print(f"⚠️ Redis cache read failed: {cache_error}")
        else:
            print(f"🔄 Force refresh requested - bypassing Redis cache")

        # Fall back to database if no Redis cache
        print(f"📦 No Redis cache, checking database for {phone_number}")
        saved_cart = db.get_latest_cart_data(phone_number)

        if saved_cart and saved_cart.get('cart_data'):
            return {
                "cart_data": saved_cart['cart_data'],
                "delivery_date": saved_cart.get('delivery_date'),
                "scraped_at": saved_cart.get('scraped_at'),
                "from_cache": False,
                "cache_type": "database",
                "swaps": [],  # Can be populated later
                "addons": []  # Can be populated later
            }
        else:
            return {"error": "No saved cart data found"}

    except Exception as e:
        print(f"Error retrieving saved cart: {e}")
        return {"error": str(e)}


def categorize_item(item_name: str) -> str:
    """
    Categorize FTP items by Cook's Box categories for category-aware swaps.

    Args:
        item_name: Name of the item to categorize

    Returns:
        Category: 'protein', 'produce', or 'grocery'
    """
    item_lower = item_name.lower()

    # Protein items (meat, fish, poultry, eggs)
    if any(protein in item_lower for protein in [
        'chicken', 'turkey', 'beef', 'pork', 'lamb', 'salmon', 'cod', 'halibut',
        'redfish', 'tuna', 'shrimp', 'scallops', 'mussels', 'eggs', 'tofu'
    ]):
        return 'protein'

    # Grocery items (grains, legumes, nuts, oils, dairy, pantry staples)
    if any(grocery in item_lower for grocery in [
        'quinoa', 'rice', 'pasta', 'beans', 'lentils', 'chickpeas', 'nuts', 'seeds',
        'oil', 'vinegar', 'honey', 'maple syrup', 'flour', 'oats', 'barley',
        'cheese', 'yogurt', 'milk', 'butter', 'cream', 'cottage cheese', 'ricotta'
    ]):
        return 'grocery'

    # Everything else is produce (fruits, vegetables, herbs)
    return 'produce'


async def generate_swaps_async(cart_data: dict, user_preferences: dict, normalized_phone: str) -> list:
    """
    Generate swaps asynchronously for parallel execution.

    Args:
        cart_data: Cart data containing selected items and alternatives
        user_preferences: User preferences for personalization
        normalized_phone: Normalized phone number for swap history

    Returns:
        List of swap suggestions
    """
    try:
        import openai
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            print("⚠️ No OpenAI API key for swap generation")
            return []

        client = openai.OpenAI(api_key=openai_key)

        # Build context for GPT-5 with category awareness
        selected_items = []
        available_alternatives = []
        selected_by_category = {"protein": [], "produce": [], "grocery": []}
        alternatives_by_category = {"protein": [], "produce": [], "grocery": []}

        # Collect from customizable_boxes array
        for box in cart_data.get("customizable_boxes", []):
            for item in box.get("selected_items", []):
                item_name = item["name"]
                selected_items.append(item_name)
                # Use scraped category if available, else fallback to guessing
                category = item.get("category")
                if not category:
                    category = categorize_item(item_name)
                selected_by_category[category].append(item_name)

            for item in box.get("available_alternatives", []):
                item_name = item["name"]
                available_alternatives.append(item_name)
                # Use scraped category if available, else fallback
                category = item.get("category")
                if not category:
                    category = categorize_item(item_name)
                alternatives_by_category[category].append(item_name)

        # ALSO collect from non_customizable_boxes for customizable ones
        for box in cart_data.get("non_customizable_boxes", []):
            if box.get("customizable") or box.get("available_alternatives"):
                for item in box.get("selected_items", []):
                    item_name = item["name"]
                    selected_items.append(item_name)
                    category = item.get("category")
                    if not category:
                        category = categorize_item(item_name)
                    selected_by_category[category].append(item_name)

                for item in box.get("available_alternatives", []):
                    item_name = item["name"]
                    available_alternatives.append(item_name)
                    category = categorize_item(item_name)
                    alternatives_by_category[category].append(item_name)

        # Extract key preferences
        liked_meals = user_preferences.get('liked_meals', [])
        cooking_methods = user_preferences.get('cooking_methods', [])
        dietary_restrictions = user_preferences.get('dietary_restrictions', [])
        health_goals = user_preferences.get('goals', [])

        # Get household size for portion calculations
        household_size = user_preferences.get('household_size', '1-2')
        servings_needed = 2 if '1-2' in str(household_size) else 4 if '3-4' in str(household_size) else 6

        # GET SWAP HISTORY to prevent ping-pong suggestions
        recent_swaps = []
        delivery_date = cart_data.get('delivery_date', '')
        if normalized_phone and delivery_date:
            try:
                # Extract date from delivery string (format: 2025-09-18T14:00:00-04:00)
                if 'T' in str(delivery_date):
                    date_part = str(delivery_date).split('T')[0]
                else:
                    date_part = str(delivery_date)[:10]

                recent_swaps = db.get_swap_history(normalized_phone, date_part, limit=5)
                if recent_swaps:
                    print(f"📋 Found {len(recent_swaps)} recent swaps for this delivery")
            except Exception as swap_error:
                print(f"⚠️ Could not retrieve swap history: {swap_error}")

        # Build category-aware swap constraints
        category_constraints = []
        for category in ["protein", "produce", "grocery"]:
            selected = selected_by_category[category]
            alternatives = alternatives_by_category[category]
            if selected and alternatives:
                category_constraints.append(f"- {category.upper()}: {', '.join(selected)} can only swap with {', '.join(alternatives)}")

        prompt = f"""Analyze this Farm to People cart and suggest smart swaps.

CURRENT CART BY CATEGORY:
- Proteins: {', '.join(selected_by_category['protein']) if selected_by_category['protein'] else 'None'} ({len(selected_by_category['protein'])} proteins total)
- Produce: {', '.join(selected_by_category['produce']) if selected_by_category['produce'] else 'None'}
- Grocery: {', '.join(selected_by_category['grocery']) if selected_by_category['grocery'] else 'None'}

CATEGORY SWAP CONSTRAINTS (CRITICAL - MUST FOLLOW):
{chr(10).join(category_constraints) if category_constraints else 'No swappable items available'}

⚠️ CRITICAL RULE: You can ONLY swap items within the same category:
- Protein → Protein ONLY (chicken → turkey ✓, turkey → corn ✗)
- Produce → Produce ONLY (kale → spinach ✓)
- Grocery → Grocery ONLY (beans → cheese ✓, quinoa → yogurt ✓)

USER PREFERENCES:
- Household size: {household_size} (needs {servings_needed} servings per meal)
- Liked meals: {', '.join(liked_meals[:5]) if liked_meals else 'Not specified'}
- Cooking methods: {', '.join(cooking_methods) if cooking_methods else 'Any'}
- Dietary restrictions: {', '.join(dietary_restrictions) if dietary_restrictions else 'None'}
- Health goals: {', '.join(health_goals) if health_goals else 'None'}

RECENT USER SWAPS (DO NOT REVERSE THESE):
{[f"{swap['from_item']} → {swap['to_item']}" for swap in recent_swaps] if recent_swaps else ['None - this is the first analysis']}

1. SWAPS: Suggest 1-5 swaps ONLY if they would SIGNIFICANTLY improve the cart:
   - NEVER suggest reversing a recent swap shown above (critical rule!)
   - NEVER suggest cross-category swaps (turkey → corn is INVALID)
   - NEVER suggest protein swaps for "variety" if there's only 1 protein in cart
   - Violates dietary restrictions (ALWAYS suggest swapping)
   - Poor fit for health goals (high priority)
   - Better matches preferred cuisine/cooking methods
   - Improves protein variety ONLY if cart has 2+ different proteins
   - If current cart already aligns with preferences well, return EMPTY swaps array

Return JSON format:
{{
  "swaps": [
    {{"from": "item name", "to": "alternative name", "reason": "specific reason"}}
  ]
}}"""

        # Build parameters compatible with the specific model
        from services.meal_generator import build_api_params
        token_limit = 1200 if AI_MODEL.lower().startswith("gpt-5") else 500
        api_params = build_api_params(AI_MODEL, max_tokens_value=token_limit, temperature_value=0.7)

        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": "You are a Farm to People meal planning expert. Analyze carts and suggest smart improvements based on user preferences."},
                {"role": "user", "content": prompt}
            ],
            **api_params
        )

        # Parse response (swaps only)
        import json
        import re
        gpt_response = response.choices[0].message.content.strip()
        json_match = re.search(r'\{.*\}', gpt_response, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
            swaps = result.get("swaps", [])
            return swaps
        else:
            print("⚠️ No JSON found in swap response")
            return []

    except Exception as e:
        print(f"❌ Error in async swap generation: {e}")
        return []


@app.post("/api/analyze-cart")
async def analyze_cart_api(request: Request, background_tasks: BackgroundTasks):
    """
    API endpoint for cart analysis from the dashboard.

    Applying Design of Everyday Things principles:
    - Immediate feedback (returns quickly with status)
    - Visibility of system status (can poll for updates)
    - Error prevention (validates credentials first)
    """
    import time
    api_start_time = time.time()

    try:
        data = await request.json()

        # Check if we should use mock data or real scraping
        use_mock = data.get('use_mock', False)
        phone = data.get('phone')
        force_refresh = data.get('force_refresh', False)  # New parameter!
        regenerate_only = data.get('regenerate_only', False)  # Skip scraping, just regenerate suggestions

        cart_data = None

        print(f"\n{'='*80}")
        print(f"🚀 [T+0.0s] CART ANALYSIS START - Force refresh: {force_refresh}")
        print(f"{'='*80}")

        # Enhanced timing variables for detailed breakdown
        step_timings = {}
        last_step_time = api_start_time

        def log_timing_step(step_name, description=""):
            """Log timing for each step with cumulative and step timing"""
            nonlocal last_step_time
            current_time = time.time()
            cumulative = current_time - api_start_time
            step_time = current_time - last_step_time
            step_timings[step_name] = {'cumulative': cumulative, 'step': step_time}
            desc_text = f" - {description}" if description else ""
            print(f"⏱️ [T+{cumulative:.1f}s] {step_name} (+{step_time:.1f}s){desc_text}")
            last_step_time = current_time
            return current_time

        if not use_mock and phone:
            # Try to get real cart data using stored credentials
            try:
                log_timing_step("PHONE_INPUT", f"Starting analysis for phone: {phone}")

                # Use centralized phone service for consistent normalization
                from services.phone_service import normalize_phone
                normalized_phone = normalize_phone(phone)
                log_timing_step("PHONE_NORMALIZED", f"Normalized: {phone} -> {normalized_phone}")
                
                if not normalized_phone:
                    print(f"[CART-ERROR] Invalid phone format: {phone}")
                    return {
                        "success": False,
                        "error": "Invalid phone number format",
                        "debug_info": f"Could not normalize phone: {phone}"
                    }
                
                print(f"[CART-STEP-1] Normalized: {phone} -> {normalized_phone}")

                # CRITICAL: Handle force refresh by invalidating Redis cache
                if force_refresh:
                    try:
                        from services.cache_service import CacheService
                        CacheService.invalidate_cart(normalized_phone)
                        CacheService.invalidate_cart_response(normalized_phone)
                        log_timing_step("CACHE_INVALIDATED", f"Redis cache cleared for {normalized_phone}")
                    except Exception as cache_error:
                        print(f"⚠️ Cache invalidation failed (non-critical): {cache_error}")

                # Try to get stored cart data (but don't rely on it exclusively)
                stored_cart = db.get_latest_cart_data(normalized_phone)
                if stored_cart and stored_cart.get('cart_data'):
                    log_timing_step("STORED_CART_FOUND", f"Found stored cart data for {normalized_phone}")
                else:
                    log_timing_step("STORED_CART_MISSING", f"No stored cart data for {normalized_phone}")
                
                # If regenerate_only flag is set, just use stored data (no scraping)
                if regenerate_only:
                    if stored_cart and stored_cart.get('cart_data'):
                        print("✨ Regenerate mode: Using stored cart data for new suggestions")
                        cart_data = stored_cart.get('cart_data')
                    else:
                        return {
                            "success": False,
                            "error": "No stored cart data available. Please analyze your cart first.",
                            "debug_info": "regenerate_only requires existing cart data"
                        }
                else:
                    # REMOVED ALL CART LOCK LOGIC - Always try to scrape fresh data
                    cart_data = None
                
                # Check if we should use stored data or try to scrape
                use_stored_data = data.get('use_stored', False)
                
                # Skip all scraping logic if we're in regenerate_only mode
                if not regenerate_only:
                    # Use the normalized phone to find user
                    user_record = db.get_user_by_phone(normalized_phone)
                    if user_record:
                        print(f"  ✅ Found user with normalized phone: {normalized_phone}")
                    else:
                        print(f"  ⚠️ No user found for {normalized_phone}")
                    
                    # Try live scraping first if we have credentials
                    if user_record and user_record.get('ftp_email'):
                        # Get user credentials from database (only if we don't already have cart_data)
                        email = user_record['ftp_email']
                        # Decrypt password using proper encryption service
                        from services.encryption_service import PasswordEncryption
                        encoded_pwd = user_record.get('ftp_password_encrypted', '')

                        # Try to decrypt password with proper decryption service
                        password = None
                        if encoded_pwd:
                            try:
                                password = PasswordEncryption.decrypt_password(encoded_pwd)
                                if password:
                                    print(f"✅ Successfully decrypted password for {email}")
                                else:
                                    print(f"⚠️ Password decryption returned None for {email}")
                            except Exception as decrypt_error:
                                print(f"⚠️ Failed to decrypt password: {decrypt_error}")
                                print(f"⚠️ Encrypted password length: {len(encoded_pwd)}")
                                # Don't fail completely - maybe stored cart has data
                        
                        if email and password:
                            log_timing_step("SCRAPER_CREDENTIALS_READY", f"Starting live scraper for {email}")
                            # Run the actual scraper with return_data=True (properly isolated from async context)
                            credentials = {'email': email, 'password': password}

                            # Add timeout and comprehensive logging
                            import asyncio
                            try:
                                scraper_start_time = log_timing_step("SCRAPER_START", "Starting scraper with 120s timeout")
                                # Use async scraper directly with normalized phone
                                cart_data = await asyncio.wait_for(
                                    run_cart_scraper(
                                        credentials,
                                        return_data=True,
                                        phone_number=normalized_phone,
                                        force_save=force_refresh  # Pass force_refresh to ensure database save
                                    ),
                                    timeout=120.0  # 2 minute timeout
                                )
                                scraper_duration = time.time() - scraper_start_time
                                log_timing_step("SCRAPER_COMPLETE", f"Scraper completed in {scraper_duration:.1f}s")
                            except asyncio.TimeoutError:
                                print(f"⏰ Scraper timed out after 120 seconds - using fallback data")
                                cart_data = None
                            except Exception as scraper_error:
                                print(f"❌ Scraper failed with error: {scraper_error}")
                                cart_data = None
                            
                            if cart_data:
                                print("✅ Successfully scraped live cart data!")

                                # CRITICAL: Cache fresh cart data to Redis immediately
                                try:
                                    from services.cache_service import CacheService
                                    CacheService.set_cart(normalized_phone, cart_data, ttl=7200)  # 2 hour cache
                                    print(f"🔥 Fresh cart data cached to Redis for {normalized_phone}")
                                except Exception as cache_error:
                                    print(f"⚠️ Redis cache failed (non-critical): {cache_error}")

                                # Check if cart is missing customizable boxes (likely locked)
                                has_customizable = cart_data.get('customizable_boxes') and len(cart_data['customizable_boxes']) > 0
                                
                                if not has_customizable:
                                    print("⚠️ Cart appears empty (no customizable boxes).")
                                    # Use the stored cart if we already have it
                                    if stored_cart and stored_cart.get('cart_data'):
                                        stored_has_customizable = (stored_cart['cart_data'].get('customizable_boxes') and 
                                                                  len(stored_cart['cart_data']['customizable_boxes']) > 0)
                                        
                                        if stored_has_customizable:
                                            print("✅ Using previously stored cart data with complete boxes")
                                            cart_data = stored_cart['cart_data']
                                        else:
                                            print("⚠️ Stored cart also has no customizable boxes")
                            else:
                                # Scraper returned no data or timed out - use fallback
                                print("⚠️ Scraper returned no data or timed out.")
                                if stored_cart and stored_cart.get('cart_data'):
                                    print("✅ Using previously stored cart data as fallback")
                                    cart_data = stored_cart['cart_data']
                                else:
                                    # Return error if no data available
                                    return {
                                        "success": False,
                                        "error": "Scraper timed out and no stored cart data available. Please try again or check your Farm to People account.",
                                        "debug_info": "Scraper timeout/failure and no stored data found"
                                    }
                        else:
                            # Return error instead of mock data
                            return {
                                "success": False,
                                "error": "Missing Farm to People credentials. Please log in first.",
                                "debug_info": f"User found but no credentials stored for {email if 'email' in locals() else 'unknown'}"
                            }
                    elif not cart_data:
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
        
        # Determine if fresh data was scraped (to trigger localStorage clear)
        fresh_scrape = cart_data is not None and not regenerate_only

        # Initialize variables
        swaps = []
        meals = None
        addons = []

        # If using stored cart data (fallback), try to get cached data
        if not fresh_scrape and normalized_phone:
            try:
                from services.cache_service import CacheService
                cached_response = CacheService.get_cart_response(normalized_phone)
                if cached_response:
                    cached_swaps = cached_response.get('swaps', [])
                    cached_addons = cached_response.get('addons', [])
                    if cached_swaps or cached_addons:
                        swaps = cached_swaps
                        addons = cached_addons
                        print(f"✅ Using cached swaps ({len(swaps)}) and addons ({len(addons)}) from last successful scrape")
            except Exception as cache_error:
                print(f"⚠️ Could not load cached swaps/addons: {cache_error}")
                # Keep empty arrays as fallback
        
        # Get user preferences for personalized meal generation
        # IMPORTANT: This feeds into the Meals tab - consistent user lookup is critical
        # for meal personalization (high-protein, quick dinners, dietary restrictions)
        user_preferences = {}
        if phone:
            try:
                # Normalize once for consistent user lookup
                if not normalized_phone:  # May already be normalized from above
                    from services.phone_service import normalize_phone
                    normalized_phone = normalize_phone(phone)
                
                if normalized_phone:
                    user_record = db.get_user_by_phone(normalized_phone)
                    if user_record:
                        user_preferences = user_record.get('preferences', {})
                        print(f"✅ Loaded preferences for meal generation: {list(user_preferences.keys())}")
                    else:
                        print(f"⚠️ No preferences found for {normalized_phone} - using defaults")
            except Exception as e:
                print(f"⚠️ Error loading preferences: {e}")
        
        # Use GPT-5 to generate smart swaps and add-ons
        swaps_start_time = log_timing_step("SWAPS_START", "Starting swap generation")

        # Check both arrays for boxes with alternatives (fixed from only checking customizable_boxes)
        has_alternatives = False
        customizable_count = 0
        non_customizable_with_alternatives = 0

        if cart_data:
            # Check customizable_boxes array
            customizable_boxes = cart_data.get("customizable_boxes", [])
            if customizable_boxes:
                has_alternatives = True
                customizable_count = len(customizable_boxes)
                print(f"🔍 SWAP DEBUG: Found {customizable_count} customizable boxes")
            else:
                print("🔍 SWAP DEBUG: No customizable_boxes found")

            # Also check non_customizable_boxes for boxes with alternatives
            non_customizable_boxes = cart_data.get("non_customizable_boxes", [])
            print(f"🔍 SWAP DEBUG: Checking {len(non_customizable_boxes)} non-customizable boxes")

            for i, box in enumerate(non_customizable_boxes):
                box_has_alternatives = box.get("available_alternatives") or box.get("customizable")
                print(f"🔍 SWAP DEBUG: Box {i+1}: has_alternatives={bool(box.get('available_alternatives'))}, customizable={bool(box.get('customizable'))}")
                if box_has_alternatives:
                    has_alternatives = True
                    non_customizable_with_alternatives += 1

            print(f"🔍 SWAP DEBUG SUMMARY: has_alternatives={has_alternatives}, customizable_count={customizable_count}, non_customizable_with_alternatives={non_customizable_with_alternatives}")
        else:
            print("🔍 SWAP DEBUG: No cart_data provided")

        if has_alternatives:
            try:
                import openai
                openai_key = os.getenv("OPENAI_API_KEY")
                if openai_key:
                    client = openai.OpenAI(api_key=openai_key)
                    log_timing_step("SWAPS_PROMPT_BUILD", "Building GPT-5 swap prompt")

                    # Build category-aware context for GPT-5 to prevent cross-category swaps
                    from collections import defaultdict

                    def categorize_item_simple(item_name):
                        """Quick categorization for swap context"""
                        name_lower = item_name.lower()
                        if any(protein in name_lower for protein in ['chicken', 'beef', 'turkey', 'fish', 'salmon', 'pork', 'sausage', 'egg']):
                            return 'protein'
                        elif any(produce in name_lower for produce in ['tomato', 'pepper', 'kale', 'lettuce', 'carrot', 'zucchini', 'onion', 'broccoli', 'spinach', 'arugula', 'cauliflower']):
                            return 'produce'
                        else:
                            return 'grocery'  # Rice, beans, pasta, etc.

                    # Category-aware collection
                    selected_by_category = defaultdict(list)
                    alternatives_by_category = defaultdict(list)

                    # Collect from customizable_boxes array with categories
                    for box in cart_data.get("customizable_boxes", []):
                        for item in box.get("selected_items", []):
                            category = categorize_item_simple(item["name"])
                            selected_by_category[category].append(item["name"])
                        for item in box.get("available_alternatives", []):
                            category = categorize_item_simple(item["name"])
                            alternatives_by_category[category].append(item["name"])

                    # ALSO collect from non_customizable_boxes for customizable ones
                    for box in cart_data.get("non_customizable_boxes", []):
                        if box.get("customizable") or box.get("available_alternatives"):
                            for item in box.get("selected_items", []):
                                category = categorize_item_simple(item["name"])
                                selected_by_category[category].append(item["name"])
                            for item in box.get("available_alternatives", []):
                                category = categorize_item_simple(item["name"])
                                alternatives_by_category[category].append(item["name"])

                    # Extract key preferences
                    liked_meals = user_preferences.get('liked_meals', [])
                    cooking_methods = user_preferences.get('cooking_methods', [])
                    dietary_restrictions = user_preferences.get('dietary_restrictions', [])
                    health_goals = user_preferences.get('goals', [])

                    # Get household size for portion calculations
                    household_size = user_preferences.get('household_size', '1-2')
                    servings_needed = 2 if '1-2' in str(household_size) else 4 if '3-4' in str(household_size) else 6

                    # GET SWAP HISTORY to prevent ping-pong suggestions
                    recent_swaps = []
                    delivery_date = cart_data.get('delivery_date', '')
                    if normalized_phone and delivery_date:
                        try:
                            # Extract date from delivery string (format: 2025-09-18T14:00:00-04:00)
                            if 'T' in str(delivery_date):
                                date_part = str(delivery_date).split('T')[0]
                            else:
                                date_part = str(delivery_date)[:10]

                            recent_swaps = db.get_swap_history(normalized_phone, date_part, limit=5)
                            if recent_swaps:
                                print(f"📋 Found {len(recent_swaps)} recent swaps for this delivery")
                        except Exception as swap_error:
                            print(f"⚠️ Could not retrieve swap history: {swap_error}")

                    # Build category-separated context for the prompt
                    cart_summary = []
                    swap_options = []

                    for category in ['protein', 'produce', 'grocery']:
                        if selected_by_category[category]:
                            cart_summary.append(f"{category.upper()}: {', '.join(selected_by_category[category])}")
                        if alternatives_by_category[category]:
                            swap_options.append(f"{category.upper()} alternatives: {', '.join(alternatives_by_category[category])}")

                    prompt = f"""Analyze this Farm to People cart and suggest smart swaps.

CURRENT CART BY CATEGORY:
{chr(10).join(cart_summary)}

AVAILABLE SWAP OPTIONS BY CATEGORY:
{chr(10).join(swap_options)}

USER PREFERENCES:
- Household size: {household_size} (needs {servings_needed} servings per meal)
- Liked meals: {', '.join(liked_meals[:5]) if liked_meals else 'Not specified'}
- Cooking methods: {', '.join(cooking_methods) if cooking_methods else 'Any'}
- Dietary restrictions: {', '.join(dietary_restrictions) if dietary_restrictions else 'None'}
- Health goals: {', '.join(health_goals) if health_goals else 'None'}

RECENT USER SWAPS (DO NOT REVERSE THESE):
{[f"{swap['from_item']} → {swap['to_item']}" for swap in recent_swaps] if recent_swaps else ['None - this is the first analysis']}

CRITICAL SWAP RULES:
- **ONLY SWAP WITHIN SAME CATEGORY**: Protein → Protein, Produce → Produce, Grocery → Grocery
- **NEVER cross categories**: Don't swap cauliflower (produce) for rice (grocery)
- **NEVER swap protein for produce or grocery items**
- Portion sizes: 0.6-1lb chicken thighs serves 2 people for ONE meal only
- 1lb sausage serves 3-4 people for one meal
- Don't suggest swapping items that were already swapped
- CONSOLIDATION: Consider swapping variety for simplicity within same category
  Example: If they have zucchini and kale (both produce), suggest swapping kale for another zucchini
  This gives them 2 units of zucchini instead of 1 each of different vegetables

TASK:
First, analyze if the current cart already aligns well with the user's preferences:
- If liked meals match current cart items closely, consider fewer/no swaps
- If dietary restrictions are already satisfied, don't suggest unnecessary changes
- If health goals are already met by current selections, minimize swaps

1. SWAPS: Suggest 1-5 swaps ONLY if they would SIGNIFICANTLY improve the cart:
   - NEVER suggest reversing a recent swap shown above (critical rule!)
   - NEVER suggest protein swaps for "variety" if there's only 1 protein in cart
   - Violates dietary restrictions (ALWAYS suggest swapping)
   - Poor fit for health goals (high priority)
   - Better matches preferred cuisine/cooking methods
   - Improves protein variety ONLY if cart has 2+ different proteins
   - Better recipe compatibility with other ingredients
   - If current cart already aligns with preferences well, return EMPTY swaps array
   - Quality over quantity: Better to suggest 0 swaps than random ones

Return JSON format (generate appropriate suggestions based on cart):
{{
  "swaps": [
    {{"from": "item name", "to": "alternative name", "reason": "specific reason"}}
  ]
}}
"""

                    # Build parameters compatible with the specific model
                    # Use higher token limit for GPT-5 to account for reasoning tokens
                    token_limit = 1200 if AI_MODEL.lower().startswith("gpt-5") else 500
                    api_params = build_api_params(AI_MODEL, max_tokens_value=token_limit, temperature_value=0.7)
                    print(f"📝 [CART ANALYSIS DEBUG] Using token limit: {token_limit} for {AI_MODEL}")

                    log_timing_step("SWAPS_GPT_CALL", "Calling GPT-5 API for swaps")

                    response = client.chat.completions.create(
                        model=AI_MODEL,
                        messages=[
                            {"role": "system", "content": "You are a Farm to People meal planning expert. Analyze carts and suggest smart improvements based on user preferences."},
                            {"role": "user", "content": prompt}
                        ],
                        **api_params
                    )

                    elapsed = time.time() - api_start_time
                    gpt_time = time.time() - gpt_swap_start
                    print(f"⏱️ [T+{elapsed:.1f}s] GPT-5 swap response received (API took {gpt_time:.1f}s)")
                    
                    # Parse response (swaps only now)
                    import json
                    import re
                    gpt_response = response.choices[0].message.content.strip()
                    json_match = re.search(r'\{.*\}', gpt_response, re.DOTALL)
                    if json_match:
                        result = json.loads(json_match.group())
                        swaps = result.get("swaps", [])
                        elapsed = time.time() - api_start_time
                        print(f"⏱️ [T+{elapsed:.1f}s] Generated {len(swaps)} swaps via GPT-5")
                    
            except Exception as e:
                print(f"⚠️ Could not generate AI swaps: {e}")
                # Return empty swaps/addons rather than hardcoded ones
                pass
        else:
            print("🔍 SWAP DEBUG: No alternatives available - skipping swap generation")
            print("🔍 SWAP DEBUG: This is normal for carts with only fixed/non-customizable items")
        
        # Handle meal suggestions
        meals_start_time = log_timing_step("MEALS_START", "Starting meal generation phase")

        meals = None
        if fresh_scrape and cart_data and normalized_phone:
            # Fresh scrape - generate new meals automatically
            meal_gen_start = time.time()
            try:
                from services.meal_generator import generate_meals
                user_record = db.get_user_by_phone(normalized_phone)
                user_preferences = user_record.get('preferences', {}) if user_record else {}

                log_timing_step("MEALS_GPT_START", "Fresh cart detected - calling GPT-5 for meals")
                result = await generate_meals(cart_data, preferences=user_preferences)
                if result['success']:
                    meals = result['meals']
                    # Extract add-ons from meal generator result
                    if 'addons' in result and result['addons']:
                        addons = result['addons']
                        print(f"✅ Received {len(addons)} add-ons from meal generator")
                    log_timing_step("MEALS_GPT_COMPLETE", f"Generated {len(meals)} meals and {len(addons)} add-ons")

                    # Cache the newly generated meals
                    cache_start = time.time()
                    from services.cache_service import CacheService
                    CacheService.set_meals(normalized_phone, meals, ttl=7200)
                    elapsed = time.time() - api_start_time
                    print(f"⏱️ [T+{elapsed:.1f}s] Cached meals to Redis (took {time.time() - cache_start:.2f}s)")

                    # Initialize meal locks data structure
                    try:
                        meal_count = len([m for m in meals if m.get('type') != 'snack'])
                        snack_count = len([m for m in meals if m.get('type') == 'snack'])
                        CacheService.initialize_meal_locks(normalized_phone, meals, cart_data, meal_count, snack_count)
                        print(f"🔒 Initialized meal locks for {len(meals)} meals ({meal_count} meals, {snack_count} snacks)")
                    except Exception as lock_error:
                        print(f"⚠️ Error initializing meal locks: {lock_error}")

                    # Generate meal-aware add-ons after meals are created
                    addons_start = time.time()
                    try:
                        elapsed = time.time() - api_start_time
                        print(f"⏱️ [T+{elapsed:.1f}s] Generating meal-aware add-ons...")
                        from services.meal_generator import generate_meal_addons
                        addons = await generate_meal_addons(meals, cart_data, user_preferences)
                        elapsed = time.time() - api_start_time
                        addons_time = time.time() - addons_start
                        print(f"⏱️ [T+{elapsed:.1f}s] Generated {len(addons)} meal-aware add-ons (took {addons_time:.1f}s)")
                    except Exception as addon_error:
                        print(f"⚠️ Error generating add-ons: {addon_error}")
                        # Fallback to basic add-ons
                        addons = [
                            {"item": "Fresh Italian Parsley", "price": "$2.50", "reason": "Versatile herb for garnishing", "category": "produce"},
                            {"item": "Fresh Lemons", "price": "$3.00", "reason": "Brightens any dish", "category": "produce"}
                        ]
                else:
                    print(f"⚠️ Failed to generate meals: {result.get('error', 'Unknown error')}")
            except Exception as meal_error:
                print(f"⚠️ Error generating meals for fresh cart: {meal_error}")
        elif not fresh_scrape and normalized_phone:
            # Page refresh - load cached meals
            try:
                from services.cache_service import CacheService
                meals = CacheService.get_meals(normalized_phone)
                if meals:
                    print(f"💾 Loaded {len(meals)} cached meals from Redis")
                else:
                    print(f"📦 No cached meals found for {normalized_phone}")
            except Exception as cache_error:
                print(f"⚠️ Error loading cached meals: {cache_error}")

        # Build complete response
        response_start = time.time()
        elapsed = response_start - api_start_time
        print(f"⏱️ [T+{elapsed:.1f}s] Building complete response...")

        complete_response = {
            "success": True,
            "cart_data": cart_data,
            "swaps": swaps,
            "addons": addons,
            "meals": meals,  # Include meals in response
            "fresh_scrape": fresh_scrape,  # Flag for frontend to clear localStorage
            "force_refresh": force_refresh,  # Echo back for debugging
            "delivery_date": cart_data.get('delivery_date') if cart_data else None,  # Include delivery date in cache
            "scraped_at": cart_data.get('scraped_timestamp') if cart_data else None  # Include timestamp
        }

        # CRITICAL: Cache complete response to Redis (includes swaps & addons)
        # Validate cart_data contains valid customizable boxes before caching
        cache_operations_start = time.time()

        def is_valid_cart_data(cart_data):
            """Validate that cart_data has customizable boxes with selected_items"""
            if not cart_data:
                return False

            customizable_boxes = cart_data.get('customizable_boxes', [])
            if not customizable_boxes:
                return False

            # Check that at least one customizable box has selected_items
            for box in customizable_boxes:
                selected_items = box.get('selected_items', [])
                if selected_items and len(selected_items) > 0:
                    return True

            return False

        if (normalized_phone and cart_data and swaps is not None and addons is not None and
            is_valid_cart_data(cart_data)):
            redis_cache_start = time.time()
            try:
                from services.cache_service import CacheService
                CacheService.set_cart_response(normalized_phone, complete_response, ttl=7200)
                elapsed = time.time() - api_start_time
                print(f"⏱️ [T+{elapsed:.1f}s] Complete cart response cached to Redis (took {time.time() - redis_cache_start:.2f}s)")
            except Exception as cache_error:
                print(f"⚠️ Complete response cache failed (non-critical): {cache_error}")

            # Save analysis to database for persistence beyond Redis TTL
            db_save_start = time.time()
            try:
                metadata = {
                    "fresh_scrape": fresh_scrape,
                    "force_refresh": force_refresh,
                    "scraped_at": cart_data.get('scraped_timestamp'),
                    "processing_time_seconds": time.time() - api_start_time
                }
                db.save_cart_analysis(
                    phone_number=normalized_phone,
                    cart_data=cart_data,
                    meal_suggestions=meals if meals else [],
                    add_ons=addons if addons else [],
                    swaps=swaps if swaps else [],
                    delivery_date=cart_data.get('delivery_date'),
                    metadata=metadata
                )
                elapsed = time.time() - api_start_time
                print(f"⏱️ [T+{elapsed:.1f}s] Cart analysis persisted to database (took {time.time() - db_save_start:.2f}s)")
            except Exception as db_error:
                print(f"⚠️ Database save failed (non-critical): {db_error}")
        elif normalized_phone:
            print(f"⚠️ Skipping cache - invalid cart_data structure (missing selected_items in customizable boxes)")

        total_elapsed = log_timing_step("ANALYSIS_COMPLETE", "Cart analysis finished")

        # Enhanced timing summary with detailed breakdown
        print(f"\n{'='*80}")
        print(f"⏱️ DETAILED TIMING BREAKDOWN (Total: {total_elapsed:.1f}s)")
        print(f"{'='*80}")

        for step_name, timing in step_timings.items():
            print(f"  {step_name:<25} : {timing['cumulative']:>6.1f}s (+{timing['step']:>5.1f}s)")

        print(f"{'='*80}")
        print(f"🎯 PERFORMANCE TARGET: Under 35s (Current: {total_elapsed:.1f}s)")
        print(f"{'='*80}\n")

        return complete_response
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/refresh-meals")
async def refresh_meal_suggestions(request: Request):
    """
    Generate new meal suggestions from the same cart data.
    
    This allows users to get different meal ideas without re-analyzing their cart.
    Limited to prevent abuse (track refresh count on frontend).
    """
    from services.meal_generator import generate_meals
    from services.phone_service import normalize_phone
    
    try:
        data = await request.json()
        cart_data = data.get('cart_data')
        phone = data.get('phone')
        
        if not cart_data:
            return {"success": False, "error": "No cart data provided"}
        
        # Get user preferences for personalized meal generation
        user_preferences = {}
        if phone:
            normalized_phone = normalize_phone(phone)
            if normalized_phone:
                user_record = db.get_user_by_phone(normalized_phone)
                if user_record:
                    user_preferences = user_record.get('preferences', {})
                    print(f"✅ Loaded preferences for meal refresh")
        
        # Use meal generator service
        result = await generate_meals(cart_data, preferences=user_preferences)

        if result['success']:
            # Cache the newly generated meals to Redis
            try:
                from services.cache_service import CacheService
                CacheService.set_meals(normalized_phone, result['meals'], ttl=7200)
                print(f"🔥 Cached {len(result['meals'])} refreshed meals to Redis")

                # Re-initialize meal locks data structure (clears existing locks)
                meal_count = len([m for m in result['meals'] if m.get('type') != 'snack'])
                snack_count = len([m for m in result['meals'] if m.get('type') == 'snack'])
                CacheService.initialize_meal_locks(normalized_phone, result['meals'], cart_data, meal_count, snack_count)
                print(f"🔒 Re-initialized meal locks for {len(result['meals'])} refreshed meals")
            except Exception as cache_error:
                print(f"⚠️ Failed to cache refreshed meals or initialize locks: {cache_error}")

            return {
                "success": True,
                "meals": result['meals'],
                "household_size": user_preferences.get('household_size', '2 people')
            }
        else:
            return result
        
    except Exception as e:
        print(f"❌ Error in refresh meals: {e}")
        return {"success": False, "error": str(e)}

# OLD CODE REMOVED - Meal generation logic moved to services/meal_generator.py
# The refresh-meals endpoint now uses the meal_generator service

@app.post("/api/regenerate-simple-meal")
async def regenerate_simple_meal(request: Request):
    """
    Generate a single meal suggestion for the simple meal card.

    This provides quick meal inspiration without generating full weekly plans.
    Used by the Meals tab for instant meal ideas.
    """
    from services.meal_generator import generate_single_meal
    from services.phone_service import normalize_phone

    try:
        data = await request.json()
        cart_data = data.get('cart_data')
        phone = data.get('phone')

        if not cart_data:
            return {"success": False, "error": "No cart data provided"}

        # Get user preferences for personalized meal generation
        user_preferences = {}
        if phone:
            normalized_phone = normalize_phone(phone)
            if normalized_phone:
                user_record = db.get_user_by_phone(normalized_phone)
                if user_record:
                    user_preferences = user_record.get('preferences', {})

        # Generate a single meal using available ingredients
        result = await generate_single_meal(cart_data, user_preferences)

        if result['success']:
            return {
                "success": True,
                "meal": result['meal'],
                "ingredients_used": result.get('ingredients_used', [])
            }
        else:
            return result

    except Exception as e:
        print(f"❌ Error regenerating simple meal: {e}")
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
        # Use centralized phone normalization
        from services.phone_service import normalize_phone, get_phone_variants
        normalized_phone = normalize_phone(phone)
        
        if not normalized_phone:
            return {
                "success": False,
                "error": "Invalid phone number format"
            }
        
        # For backward compatibility, also check variants
        phone_formats = get_phone_variants(phone)
            
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
            "selected_meal_ids": preferences.get('selected_meal_ids', []),  # Add dish preferences
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
        elif category == "dishes":
            current_preferences['selected_meal_ids'] = value
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
        
        # Update the database record using the new preferences-only function
        updated_record = db.update_user_preferences(
            phone_number=phone,
            preferences=current_preferences
        )

        if updated_record:
            print(f"✅ Successfully updated preferences for {phone}")
            return {
                "success": True,
                "message": "Preferences updated successfully",
                "preferences": current_preferences
            }
        else:
            print(f"❌ Failed to update preferences for {phone}")
            return {"success": False, "error": "Failed to update preferences in database"}
        
    except Exception as e:
        return {"success": False, "error": str(e)}


# ===== MEAL LOCKING API ENDPOINTS =====

@app.get("/api/meal-locks")
async def get_meal_locks(phone: str):
    """
    Get meal lock status for a user.

    Args:
        phone: User's phone number (query parameter)

    Returns:
        JSON with lock status array and metadata
    """
    try:
        from services.cache_service import CacheService

        # Normalize phone number
        from services.phone_service import normalize_phone
        normalized_phone = normalize_phone(phone)

        # Get meal locks data
        meal_data = CacheService.get_meal_locks_data(normalized_phone)

        if not meal_data:
            return {
                "success": True,
                "locked_status": [],
                "has_meals": False,
                "message": "No meal data found"
            }

        return {
            "success": True,
            "locked_status": meal_data.get('locked_status', []),
            "has_meals": len(meal_data.get('generated_meals', [])) > 0,
            "meal_count": meal_data.get('meal_count', 0),
            "snack_count": meal_data.get('snack_count', 0),
            "generation_timestamp": meal_data.get('generation_timestamp'),
            "generation_source": meal_data.get('generation_source', 'cart')
        }

    except Exception as e:
        print(f"❌ Get meal locks error: {e}")
        return {"success": False, "error": str(e)}


@app.post("/api/meal-lock")
async def toggle_meal_lock(request: Request):
    """
    Toggle lock status for a specific meal.

    Request body:
        {
            "phone": "user_phone_number",
            "index": 0,
            "locked": true
        }

    Returns:
        Success status and updated lock information
    """
    try:
        from services.cache_service import CacheService
        from services.phone_service import normalize_phone

        body = await request.json()
        phone = body.get('phone')
        index = body.get('index')
        locked = body.get('locked')

        if not all([phone is not None, index is not None, locked is not None]):
            return {"success": False, "error": "Missing required fields: phone, index, locked"}

        # Normalize phone number
        normalized_phone = normalize_phone(phone)

        # Set the meal lock
        success = CacheService.set_meal_lock(normalized_phone, int(index), bool(locked))

        if success:
            # Get updated lock status
            lock_status = CacheService.get_meal_locks(normalized_phone)
            locked_ingredients = CacheService.get_locked_ingredients(normalized_phone)

            action = "locked" if locked else "unlocked"
            print(f"✅ Meal {index} {action} for {normalized_phone}")

            return {
                "success": True,
                "message": f"Meal {index} {action} successfully",
                "locked_status": lock_status,
                "locked_ingredients": locked_ingredients,
                "action": action,
                "index": index
            }
        else:
            return {"success": False, "error": "Failed to update meal lock"}

    except Exception as e:
        print(f"❌ Toggle meal lock error: {e}")
        return {"success": False, "error": str(e)}


@app.delete("/api/meal-locks")
async def clear_meal_locks(phone: str):
    """
    Clear all meal locks for a user.

    Args:
        phone: User's phone number (query parameter)

    Returns:
        Success status
    """
    try:
        from services.cache_service import CacheService
        from services.phone_service import normalize_phone

        # Normalize phone number
        normalized_phone = normalize_phone(phone)

        # Clear all locks
        success = CacheService.clear_meal_locks(normalized_phone)

        if success:
            print(f"✅ Cleared all meal locks for {normalized_phone}")
            return {
                "success": True,
                "message": "All meal locks cleared successfully",
                "locked_status": []
            }
        else:
            return {"success": False, "error": "Failed to clear meal locks"}

    except Exception as e:
        print(f"❌ Clear meal locks error: {e}")
        return {"success": False, "error": str(e)}


@app.get("/api/locked-ingredients")
async def get_locked_ingredients(phone: str):
    """
    Get ingredients used by locked meals.

    Args:
        phone: User's phone number (query parameter)

    Returns:
        JSON with categorized locked ingredients
    """
    try:
        from services.cache_service import CacheService
        from services.phone_service import normalize_phone

        # Normalize phone number
        normalized_phone = normalize_phone(phone)

        # Get locked ingredients
        locked_ingredients = CacheService.get_locked_ingredients(normalized_phone)

        return {
            "success": True,
            "locked_ingredients": locked_ingredients,
            "total_locked": sum(len(category) for category in locked_ingredients.values())
        }

    except Exception as e:
        print(f"❌ Get locked ingredients error: {e}")
        return {"success": False, "error": str(e)}


@app.get("/api/meal-locks-data")
async def get_meal_locks_data(phone: str):
    """
    Get complete meal locks data structure for debugging/admin.

    Args:
        phone: User's phone number (query parameter)

    Returns:
        Complete meal locks data structure
    """
    try:
        from services.cache_service import CacheService
        from services.phone_service import normalize_phone

        # Normalize phone number
        normalized_phone = normalize_phone(phone)

        # Get complete meal data
        meal_data = CacheService.get_meal_locks_data(normalized_phone)

        if meal_data:
            return {
                "success": True,
                "meal_data": meal_data
            }
        else:
            return {
                "success": True,
                "meal_data": None,
                "message": "No meal locks data found"
            }

    except Exception as e:
        print(f"❌ Get meal locks data error: {e}")
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
