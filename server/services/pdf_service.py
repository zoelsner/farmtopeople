"""
PDF Service
===========
Handles PDF generation and delivery for meal plans.
Extracted from server.py to isolate PDF logic.
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path


def generate_meal_plan_pdf(
    plan_data: Dict[str, Any],
    user_preferences: Dict[str, Any],
    detailed: bool = True
) -> Optional[str]:
    """
    Generate a PDF meal plan.
    
    Args:
        plan_data: Meal plan data with recipes
        user_preferences: User's cooking preferences
        detailed: Whether to include detailed recipes
        
    Returns:
        Path to generated PDF or None if failed
    """
    try:
        # Import PDF generator
        from pdf_meal_planner import generate_pdf_meal_plan
        
        # Get user skill level
        skill_level = user_preferences.get('cooking_skill_level', 'intermediate')
        
        print(f"📄 Generating PDF meal plan (detailed={detailed}, skill={skill_level})")
        
        # Generate PDF
        pdf_path = generate_pdf_meal_plan(
            generate_detailed_recipes=detailed,
            user_skill_level=skill_level
        )
        
        if pdf_path and os.path.exists(pdf_path):
            print(f"✅ PDF generated successfully: {pdf_path}")
            return pdf_path
        else:
            print("⚠️ PDF generation returned no path")
            return None
            
    except Exception as e:
        print(f"❌ PDF generation error: {e}")
        return None


def get_pdf_url(pdf_path: str, base_url: str = None) -> str:
    """
    Get the URL for a generated PDF.
    
    Args:
        pdf_path: Local path to PDF file
        base_url: Base URL of the server
        
    Returns:
        URL to access the PDF
    """
    if not base_url:
        # TODO: Get from environment or config
        base_url = os.getenv("BASE_URL", "http://localhost:8000")
    
    # Extract filename
    pdf_filename = Path(pdf_path).name
    
    # Build URL
    pdf_url = f"{base_url}/pdfs/{pdf_filename}"
    
    return pdf_url


def format_pdf_sms_message(pdf_url: str, plan_type: str = "meal") -> str:
    """
    Format an SMS message with PDF link.
    
    Args:
        pdf_url: URL to the PDF
        plan_type: Type of plan (meal, recipe, etc.)
        
    Returns:
        Formatted SMS message
    """
    if plan_type == "recipe":
        return (
            "🍽️ Your personalized recipes are ready!\n\n"
            f"📄 View your detailed recipes: {pdf_url}\n\n"
            "Each recipe includes:\n"
            "• Step-by-step instructions\n"
            "• Storage tips\n"
            "• Chef techniques\n\n"
            "Happy cooking! 👨‍🍳"
        )
    else:
        return (
            "🍽️ Your Farm to People meal plan is ready!\n\n"
            f"📄 View your complete plan: {pdf_url}\n\n"
            "Includes recipes and storage tips!\n"
            "Enjoy your meals!"
        )


def cleanup_old_pdfs(days: int = 7) -> int:
    """
    Clean up PDFs older than specified days.
    
    Args:
        days: Number of days to keep PDFs
        
    Returns:
        Number of files deleted
    """
    import time
    from datetime import datetime, timedelta
    
    pdf_dir = Path("pdfs")
    if not pdf_dir.exists():
        return 0
    
    deleted = 0
    cutoff_time = time.time() - (days * 24 * 60 * 60)
    
    for pdf_file in pdf_dir.glob("*.pdf"):
        if pdf_file.stat().st_mtime < cutoff_time:
            try:
                pdf_file.unlink()
                deleted += 1
                print(f"🗑️ Deleted old PDF: {pdf_file.name}")
            except Exception as e:
                print(f"⚠️ Could not delete {pdf_file.name}: {e}")
    
    return deleted