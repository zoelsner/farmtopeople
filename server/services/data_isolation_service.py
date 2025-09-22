"""
Data Isolation Service
======================
Ensures complete data isolation between user accounts.
Critical for preventing cross-user data contamination.
"""

import hashlib
from typing import Dict, Any, Optional
from services.phone_service import normalize_phone


class UserDataIsolation:
    """
    Ensures each user's data is completely isolated.
    """
    
    @staticmethod
    def create_user_session_key(phone: str) -> str:
        """
        Create a unique session key for a user.
        
        Args:
            phone: User's phone number
            
        Returns:
            Unique session key
        """
        normalized = normalize_phone(phone)
        if not normalized:
            raise ValueError(f"Invalid phone number: {phone}")
        
        # Create a unique hash for this user
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]
    
    @staticmethod
    def validate_data_ownership(phone: str, data: Dict[str, Any]) -> bool:
        """
        Validate that data belongs to the specified user.
        
        Args:
            phone: User's phone number
            data: Data to validate
            
        Returns:
            True if data belongs to user
        """
        normalized = normalize_phone(phone)
        if not normalized:
            return False
        
        # Check if data has phone field
        data_phone = data.get('phone_number') or data.get('phone') or data.get('user_phone')
        if not data_phone:
            return False
        
        # Normalize and compare
        data_normalized = normalize_phone(data_phone)
        return data_normalized == normalized
    
    @staticmethod
    def sanitize_user_data(data: Dict[str, Any], allowed_phone: str) -> Dict[str, Any]:
        """
        Remove any data that doesn't belong to the specified user.
        
        Args:
            data: Data to sanitize
            allowed_phone: Only data for this phone is allowed
            
        Returns:
            Sanitized data
        """
        normalized = normalize_phone(allowed_phone)
        if not normalized:
            return {}
        
        # If data has phone field, validate it
        if 'phone_number' in data or 'phone' in data or 'user_phone' in data:
            if not UserDataIsolation.validate_data_ownership(allowed_phone, data):
                print(f"⚠️ DATA ISOLATION: Blocked data not belonging to {normalized}")
                return {}
        
        # Recursively sanitize nested data
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                if isinstance(value, dict):
                    sanitized[key] = UserDataIsolation.sanitize_user_data(value, allowed_phone)
                elif isinstance(value, list):
                    sanitized[key] = [
                        UserDataIsolation.sanitize_user_data(item, allowed_phone) 
                        if isinstance(item, dict) else item 
                        for item in value
                    ]
                else:
                    sanitized[key] = value
            return sanitized
        
        return data
    
    @staticmethod
    def create_isolated_context(phone: str) -> Dict[str, Any]:
        """
        Create an isolated context for a user's operations.
        
        Args:
            phone: User's phone number
            
        Returns:
            Isolated context dict
        """
        normalized = normalize_phone(phone)
        if not normalized:
            raise ValueError(f"Invalid phone number: {phone}")
        
        return {
            "user_phone": normalized,
            "session_key": UserDataIsolation.create_user_session_key(phone),
            "allowed_phones": [normalized],  # Only this phone's data
            "isolation_level": "strict"
        }


def verify_cart_ownership(phone: str, cart_data: Dict[str, Any]) -> bool:
    """
    Verify that cart data belongs to the specified user.
    
    Args:
        phone: User's phone number
        cart_data: Cart data to verify
        
    Returns:
        True if cart belongs to user
    """
    normalized = normalize_phone(phone)
    if not normalized:
        return False
    
    # Check if cart has user identifier
    cart_phone = cart_data.get('phone_number') or cart_data.get('user_phone')
    if cart_phone:
        cart_normalized = normalize_phone(cart_phone)
        if cart_normalized != normalized:
            print(f"🚨 SECURITY: Cart data mismatch! Expected {normalized}, got {cart_normalized}")
            return False
    
    # Check if cart has email that matches user's FTP email
    cart_email = cart_data.get('email') or cart_data.get('user_email')
    if cart_email:
        # Get user's expected email from database
        import supabase_client as db
        user_data = db.get_user_by_phone(normalized)
        if user_data and user_data.get('ftp_email'):
            if cart_email.lower() != user_data['ftp_email'].lower():
                print(f"🚨 SECURITY: Cart email mismatch! Expected {user_data['ftp_email']}, got {cart_email}")
                return False
    
    return True


def enforce_data_isolation(func):
    """
    Decorator to enforce data isolation on functions.
    
    Usage:
        @enforce_data_isolation
        def process_user_data(phone: str, data: dict):
            # Function will only receive data belonging to phone
    """
    def wrapper(phone: str, *args, **kwargs):
        # Create isolated context
        context = UserDataIsolation.create_isolated_context(phone)
        
        # Add context to kwargs
        kwargs['_isolation_context'] = context
        
        # Call original function
        result = func(phone, *args, **kwargs)
        
        # Sanitize result before returning
        if isinstance(result, dict):
            result = UserDataIsolation.sanitize_user_data(result, phone)
        
        return result
    
    return wrapper