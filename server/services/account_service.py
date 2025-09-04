"""
Account Service
===============
Handles user account lookups and credential management.
Extracted from server.py to isolate account logic.
"""

import os
import base64
from typing import Dict, Any, Optional
from services.phone_service import normalize_phone
import supabase_client as db


def lookup_user_account(phone: str) -> Dict[str, Any]:
    """
    Look up user account by phone number.
    
    Args:
        phone: User's phone number (will be normalized)
        
    Returns:
        Dict with user_data and credentials or error info
    """
    # Import data isolation for security
    from services.data_isolation_service import UserDataIsolation
    
    # Normalize phone for consistent lookups
    normalized_phone = normalize_phone(phone)
    
    if not normalized_phone:
        return {
            "success": False,
            "error": "Invalid phone number format",
            "user_data": None
        }
    
    print(f"🔍 Looking up user account for: {normalized_phone}")
    
    try:
        user_data = db.get_user_by_phone(normalized_phone)
        
        if not user_data:
            print(f"❌ No user found for phone: {normalized_phone}")
            return {
                "success": False,
                "error": "Account not found. Please register first.",
                "needs_registration": True,
                "user_data": None
            }
        
        print(f"✅ User found: {user_data.get('ftp_email')}")
        
        # CRITICAL: Verify this data belongs to the requested phone
        if user_data.get('phone_number') and normalize_phone(user_data['phone_number']) != normalized_phone:
            print(f"🚨 SECURITY ALERT: Data mismatch! Requested {normalized_phone}, got {user_data['phone_number']}")
            return {
                "success": False,
                "error": "Data integrity error",
                "user_data": None
            }
        
        # Check if FTP credentials exist
        if not user_data.get('ftp_email'):
            return {
                "success": False,
                "error": "No Farm to People account linked",
                "needs_ftp_link": True,
                "user_data": user_data
            }
        
        # Decrypt password if available
        credentials = None
        if user_data.get('ftp_password_encrypted'):
            from services.encryption_service import PasswordEncryption
            
            try:
                # Use proper encryption service (handles both old base64 and new Fernet)
                password = PasswordEncryption.decrypt_password(user_data['ftp_password_encrypted'])
                
                if password:
                    credentials = {
                        'email': user_data['ftp_email'],
                        'password': password
                    }
                else:
                    print(f"⚠️ Could not decrypt password")
            except Exception as e:
                print(f"⚠️ Error decrypting password: {e}")
        
        return {
            "success": True,
            "user_data": user_data,
            "credentials": credentials,
            "preferences": user_data.get('preferences', {})
        }
        
    except Exception as e:
        print(f"❌ Error looking up user: {e}")
        return {
            "success": False,
            "error": str(e),
            "user_data": None
        }


def get_user_preferences(phone: str) -> Optional[Dict[str, Any]]:
    """
    Get user preferences for meal planning.
    
    Args:
        phone: User's phone number
        
    Returns:
        Preferences dict or None
    """
    result = lookup_user_account(phone)
    
    if result["success"] and result["user_data"]:
        return result["user_data"].get('preferences', {})
    
    return None


def check_user_needs_onboarding(user_data: Dict[str, Any]) -> bool:
    """
    Check if user needs to complete onboarding.
    
    Args:
        user_data: User data from database
        
    Returns:
        True if onboarding needed
    """
    if not user_data:
        return True
    
    preferences = user_data.get('preferences', {})
    
    # Check for minimum required preferences
    required_fields = ['household_size', 'meal_timing']
    
    for field in required_fields:
        if field not in preferences:
            return True
    
    return False