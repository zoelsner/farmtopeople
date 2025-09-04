"""
Meal Flow Service
=================
Orchestrates the complete meal plan generation flow.
This is the refactored version of the 200+ line background task.
"""

from typing import Dict, Any, Optional
from services.account_service import lookup_user_account, check_user_needs_onboarding
from services.scraper_service import scrape_user_cart
from services.pdf_service import generate_meal_plan_pdf, get_pdf_url
from services.notification_service import (
    send_progress_sms, 
    format_sms_with_help,
    send_meal_plan_sms,
    send_error_sms
)
import meal_planner
import supabase_client as db


async def run_full_meal_plan_flow(phone_number: str):
    """
    Refactored background task - orchestrates the complete meal plan flow.
    
    This was 200+ lines in server.py, now broken into logical services.
    
    Args:
        phone_number: User's phone number
    """
    print(f"🚀 Starting meal plan flow for {phone_number}")
    
    # Step 1: Account lookup
    send_progress_sms(phone_number, format_sms_with_help("🔍 Looking up your account...", 'analyzing'))
    
    account_result = lookup_user_account(phone_number)
    
    if not account_result["success"]:
        if account_result.get("needs_registration"):
            send_error_sms(phone_number, "no_account")
        elif account_result.get("needs_ftp_link"):
            send_error_sms(phone_number, "no_credentials")
        else:
            send_progress_sms(phone_number, 
                format_sms_with_help("❌ Having trouble accessing your account. Please try again.", 'error'))
        return
    
    user_data = account_result["user_data"]
    credentials = account_result.get("credentials")
    
    if not credentials:
        send_error_sms(phone_number, "no_credentials")
        return
    
    # Step 2: Check preferences
    send_progress_sms(phone_number, 
        format_sms_with_help("🔐 Found your account! Logging into Farm to People...", 'analyzing'))
    
    user_preferences = user_data.get('preferences', {})
    
    if check_user_needs_onboarding(user_data):
        # TODO: Handle preference collection flow
        print("⚠️ User needs to complete onboarding")
        # For now, use defaults
        user_preferences = {
            'household_size': '2 people',
            'meal_timing': ['dinner'],
            'dietary_restrictions': [],
            'goals': []
        }
    
    # Step 3: Scrape cart
    send_progress_sms(phone_number,
        format_sms_with_help("📦 Analyzing your current cart and customizable boxes...", 'analyzing'))
    
    cart_result = await scrape_user_cart(
        credentials=credentials,
        phone=phone_number,
        save_to_db=True
    )
    
    if not cart_result["success"]:
        send_error_sms(phone_number, "scrape_failed")
        return
    
    cart_data = cart_result["cart_data"]
    
    # Step 4: Generate meal plan
    send_progress_sms(phone_number,
        format_sms_with_help("📋 Analyzing your cart and creating strategic meal plan...", 'analyzing'))
    
    try:
        # Use the existing meal planner (keeping same logic)
        skill_level = user_preferences.get('cooking_skill_level', 'intermediate')
        plan = meal_planner.run_main_planner(
            cart_data=cart_data,
            user_preferences=user_preferences,
            generate_detailed_recipes=True,
            user_skill_level=skill_level
        )
        
        if not plan or not plan.get("meals"):
            send_error_sms(phone_number, "meal_failed")
            return
        
        # Save meal suggestions to database
        if plan.get('meals'):
            try:
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
                
                db.save_latest_cart_data(
                    phone_number=phone_number,
                    cart_data=cart_data,
                    meal_suggestions=meal_suggestions
                )
                print(f"✅ Saved {len(meal_suggestions)} meal suggestions")
            except Exception as e:
                print(f"⚠️ Failed to save meal suggestions: {e}")
        
    except Exception as e:
        print(f"❌ Meal generation failed: {e}")
        send_error_sms(phone_number, "meal_failed")
        return
    
    # Step 5: Generate PDF
    pdf_path = generate_meal_plan_pdf(
        plan_data=plan,
        user_preferences=user_preferences,
        detailed=True
    )
    
    pdf_url = None
    if pdf_path:
        pdf_url = get_pdf_url(pdf_path)
        print(f"✅ PDF available at: {pdf_url}")
    
    # Step 6: Send final SMS
    send_meal_plan_sms(
        phone=phone_number,
        pdf_url=pdf_url,
        meals=plan.get('meals', [])
    )
    
    print(f"✅ Meal plan flow completed for {phone_number}")


async def run_confirmation_flow(phone_number: str):
    """
    Handle meal plan confirmation flow.
    
    Args:
        phone_number: User's phone number
    """
    print(f"🍳 Generating confirmed meal plan for {phone_number}")
    
    # Get user data
    account_result = lookup_user_account(phone_number)
    if not account_result["success"]:
        send_error_sms(phone_number, "general")
        return
    
    user_preferences = account_result.get("preferences", {})
    
    # Generate detailed PDF
    from pdf_meal_planner import generate_pdf_meal_plan
    skill_level = user_preferences.get('cooking_skill_level', 'intermediate')
    
    pdf_path = generate_pdf_meal_plan(
        generate_detailed_recipes=True,
        user_skill_level=skill_level
    )
    
    if pdf_path:
        pdf_url = get_pdf_url(pdf_path)
        
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