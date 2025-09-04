"""
Notification Service
====================
Handles SMS notifications and progress updates.
Extracted from server.py to centralize messaging.
"""

import os
from typing import Optional
import vonage


# Initialize Vonage client (same as server.py)
vonage_client = None
try:
    api_key = os.getenv("VONAGE_API_KEY")
    api_secret = os.getenv("VONAGE_API_SECRET")
    if api_key and api_secret:
        vonage_client = vonage.Client(key=api_key, secret=api_secret)
        print("✅ Vonage client initialized")
    else:
        print("⚠️ SMS disabled - missing Vonage credentials")
except Exception as e:
    print(f"⚠️ SMS disabled - Vonage init error: {e}")


def send_sms(phone_number: str, message: str) -> bool:
    """
    Send an SMS message to a phone number.
    
    Args:
        phone_number: Recipient phone number (with country code)
        message: Message text to send
        
    Returns:
        True if sent successfully
    """
    if not vonage_client:
        print(f"⚠️ SMS disabled - would send to {phone_number}: {message[:50]}...")
        return False
    
    try:
        # Remove + prefix for Vonage (same as server.py)
        to_number = phone_number.lstrip("+")
        from_number = os.getenv("VONAGE_PHONE_NUMBER", "12019773745")
        
        # Ensure from number has country code
        if not from_number.startswith("1"):
            from_number = "1" + from_number
        
        print(f"📱 Sending SMS from {from_number} to {to_number}")
        
        response = vonage_client.sms.send_message({
            "from": from_number,
            "to": to_number,
            "text": message
        })
        
        print(f"✅ SMS sent successfully: {response}")
        return True
        
    except Exception as e:
        print(f"❌ Error sending SMS: {e}")
        return False


def send_progress_sms(phone_number: str, message: str) -> bool:
    """
    Send a progress update SMS (wrapper for consistency with server.py).
    
    Args:
        phone_number: Recipient phone number
        message: Progress message
        
    Returns:
        True if sent
    """
    return send_sms(phone_number, message)


def format_sms_with_help(message: str, state: str = 'default') -> str:
    """
    Format SMS with contextual help text.
    Moved from server.py - keeping exact same logic.
    
    Args:
        message: Main message
        state: Conversation state
        
    Returns:
        Message with help text
    """
    help_text = {
        'analyzing': "━━━━━━━━━\n⏳ This takes 20-30 seconds...",
        'plan_ready': "━━━━━━━━━\n💬 Reply: CONFIRM | SWAP item | SKIP day | help",
        'greeting': "━━━━━━━━━\n💬 Text 'plan' to start | 'new' to register",
        'onboarding': "━━━━━━━━━\n💬 Reply with your cooking preferences or use the link",
        'login': "━━━━━━━━━\n💬 After login, text 'plan' for your meal plan",
        'error': "━━━━━━━━━\n💬 Text 'plan' to try again | 'help' for options",
        'default': "━━━━━━━━━\n💬 Text 'plan' to start | 'new' to register | 'help' for options"
    }
    
    return f"{message}\n{help_text.get(state, help_text['default'])}"


def send_meal_plan_sms(phone: str, pdf_url: Optional[str], meals: list) -> bool:
    """
    Send the final meal plan SMS.
    
    Args:
        phone: Recipient phone
        pdf_url: URL to PDF if available
        meals: List of meal dicts
        
    Returns:
        True if sent
    """
    if pdf_url:
        # Send link to PDF (same format as server.py)
        sms_body = (
            f"🍽️ Your professional Farm to People meal plan is ready!\n\n"
            f"📄 View your complete plan with storage tips and recipes: {pdf_url}\n\n"
            f"Enjoy your meals!"
        )
    elif meals:
        # Send text version
        sms_body = "🍽️ Your Farm to People meal plan is ready!\n\n"
        for meal in meals:
            sms_body += f"- {meal.get('title', meal.get('name', 'Meal'))}\n"
        sms_body += "\nEnjoy your meals!"
    else:
        sms_body = "Sorry, I had trouble generating a meal plan. Please try again later."
    
    return send_sms(phone, sms_body)


def send_error_sms(phone: str, error_type: str = "general") -> bool:
    """
    Send error notification SMS.
    
    Args:
        phone: Recipient phone
        error_type: Type of error
        
    Returns:
        True if sent
    """
    messages = {
        "no_account": "❌ Account not found. Please text 'FEED ME' to get set up first!",
        "no_credentials": "❌ Please connect your Farm to People account first.",
        "scrape_failed": "❌ Having trouble accessing your cart. Please check your Farm to People account and try again.",
        "meal_failed": "❌ Error analyzing your cart. Please try again in a moment.",
        "general": "❌ Something went wrong. Please try again later."
    }
    
    message = messages.get(error_type, messages["general"])
    return send_sms(phone, format_sms_with_help(message, 'error'))