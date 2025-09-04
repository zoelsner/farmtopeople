"""
SMS Handler Service
==================
Handles SMS message routing and formatting.
Extracted from server.py to isolate SMS logic.
"""

import os
from typing import Tuple
from services.phone_service import normalize_phone
import supabase_client as db


def format_sms_with_help(message: str, state: str = 'default') -> str:
    """
    Format SMS responses with contextual help text.
    
    Args:
        message: Main message to send
        state: Current conversation state
        
    Returns:
        Formatted message with help text
    """
    help_texts = {
        'greeting': """
━━━━━━━━━
Reply with:
• "plan" - Get meal plans
• "new" - Sign up
• "help" - More options""",
        
        'analyzing': """
━━━━━━━━━
⏳ This takes 20-30 seconds. You'll receive:
• 5 personalized meals
• Link to full recipes
• Shopping list""",
        
        'plan_ready': """
━━━━━━━━━
Reply with:
• "save" - Save this plan
• "new plan" - Try different meals
• "help" - More options""",
        
        'error': """
━━━━━━━━━
Reply with:
• "plan" - Try again
• "help" - Get support
• "stop" - Unsubscribe""",
        
        'default': """
━━━━━━━━━
• "plan" - Meal plans
• "help" - Support
• "stop" - Unsubscribe"""
    }
    
    help_text = help_texts.get(state, help_texts['default'])
    return f"{message}\n{help_text}"


def route_sms_message(phone: str, message: str) -> Tuple[str, bool]:
    """
    Route an incoming SMS to the appropriate handler.
    
    Args:
        phone: Sender's phone number
        message: Message text
        
    Returns:
        Tuple of (response_message, should_trigger_background_task)
    """
    # Normalize phone for consistent lookups
    normalized_phone = normalize_phone(phone)
    if not normalized_phone:
        return ("Invalid phone number format. Please contact support.", False)
    
    # Convert to lowercase for routing
    msg_lower = message.lower().strip()
    
    # Route based on keywords
    if "stop" in msg_lower:
        return ("You've been unsubscribed. Reply START to re-subscribe.", False)
    
    elif "help" in msg_lower:
        return (format_sms_with_help(
            "📱 Farm to People AI Commands:\n\n"
            "• 'plan' - Get personalized meal plans\n"
            "• 'new' - Create account\n"
            "• 'stop' - Unsubscribe",
            'default'
        ), False)
    
    elif "plan" in msg_lower or "meal" in msg_lower:
        # Check if user exists
        user = db.get_user_by_phone(normalized_phone)
        if not user:
            return (format_sms_with_help(
                "👋 Welcome! You need an account first.\n"
                f"Visit: https://farmtopeople.ai/onboard?phone={normalized_phone}",
                'greeting'
            ), False)
        
        # User exists - trigger meal plan generation
        return (format_sms_with_help(
            "📦 Analyzing your Farm to People cart...",
            'analyzing'
        ), True)  # True = trigger background task
    
    elif "new" in msg_lower or "start" in msg_lower:
        return (format_sms_with_help(
            f"👋 Welcome to Farm to People AI!\n\n"
            f"Let's set up your meal planning:\n"
            f"https://farmtopeople.ai/onboard?phone={normalized_phone}\n\n"
            f"Takes just 2 minutes!",
            'greeting'
        ), False)
    
    elif "hello" in msg_lower or "hi" in msg_lower:
        return (format_sms_with_help(
            "👋 Hi! I'm your Farm to People meal planning assistant.",
            'greeting'
        ), False)
    
    else:
        return (format_sms_with_help(
            f"🤔 I didn't understand '{message[:20]}...'",
            'default'
        ), False)