"""
Phone Number Normalization Service
==================================
Centralizes all phone number handling to prevent format mismatches.
All phone numbers in the system should go through this service.

Standard format: +1XXXXXXXXXX (E.164 format for US numbers)
"""

import re
from typing import Optional, List


def normalize_phone(phone: str) -> Optional[str]:
    """
    Normalize any phone number format to +1XXXXXXXXXX.
    
    Args:
        phone: Phone number in any format (with or without country code, spaces, dashes, etc.)
        
    Returns:
        Normalized phone in format +1XXXXXXXXXX, or None if invalid
        
    Examples:
        >>> normalize_phone("(212) 555-1234")
        '+12125551234'
        >>> normalize_phone("2125551234")
        '+12125551234'
        >>> normalize_phone("+1 212 555 1234")
        '+12125551234'
        >>> normalize_phone("1-212-555-1234")
        '+12125551234'
    """
    if not phone:
        return None
        
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', str(phone))
    
    # Handle different digit lengths
    if len(digits) == 10:
        # US number without country code
        return f'+1{digits}'
    elif len(digits) == 11 and digits[0] == '1':
        # US number with country code
        return f'+{digits}'
    elif len(digits) == 11 and digits[0] != '1':
        # Possibly international, but we only support US for now
        return None
    else:
        # Invalid length
        return None


def get_phone_variants(phone: str) -> List[str]:
    """
    Get all possible variants of a phone number for backward compatibility.
    This is used during migration to find existing records.
    
    Args:
        phone: Phone number in any format
        
    Returns:
        List of possible phone formats that might exist in the database
        
    Example:
        >>> get_phone_variants("2125551234")
        ['+12125551234', '12125551234', '2125551234', '+2125551234']
    """
    normalized = normalize_phone(phone)
    if not normalized:
        return [phone]  # Return original if can't normalize
    
    # Remove the + for the base number
    base = normalized[1:]  # Remove leading +
    digits_only = base[1:] if base.startswith('1') else base  # Remove country code
    
    variants = [
        normalized,           # +12125551234
        base,                # 12125551234
        digits_only,         # 2125551234
        f'+{digits_only}',   # +2125551234 (incorrect but might exist)
    ]
    
    # Add original if different
    if phone not in variants:
        variants.append(phone)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_variants = []
    for v in variants:
        if v not in seen:
            seen.add(v)
            unique_variants.append(v)
    
    return unique_variants


def format_phone_display(phone: str) -> str:
    """
    Format a normalized phone number for display.
    
    Args:
        phone: Normalized phone number (+1XXXXXXXXXX)
        
    Returns:
        Formatted phone for display: (XXX) XXX-XXXX
        
    Example:
        >>> format_phone_display("+12125551234")
        '(212) 555-1234'
    """
    normalized = normalize_phone(phone)
    if not normalized:
        return phone  # Return as-is if can't normalize
    
    # Extract the 10-digit US number
    digits = normalized[2:]  # Remove +1
    
    if len(digits) == 10:
        return f'({digits[:3]}) {digits[3:6]}-{digits[6:]}'
    else:
        return phone  # Return as-is if unexpected format


def validate_us_phone(phone: str) -> bool:
    """
    Validate if a phone number is a valid US phone number.
    
    Args:
        phone: Phone number in any format
        
    Returns:
        True if valid US phone number, False otherwise
    """
    normalized = normalize_phone(phone)
    if not normalized:
        return False
    
    # Check if it starts with +1 and has 11 total digits
    if not normalized.startswith('+1') or len(normalized) != 12:
        return False
    
    # Extract area code and check if valid (not starting with 0 or 1)
    area_code = normalized[2:5]
    if area_code[0] in '01':
        return False
    
    # Extract exchange and check if valid (not starting with 0 or 1)
    exchange = normalized[5:8]
    if exchange[0] in '01':
        return False
    
    return True


# Migration helper
def migrate_phone_in_database(old_phone: str) -> str:
    """
    Helper function to migrate old phone formats to normalized format.
    
    Args:
        old_phone: Phone number in old/inconsistent format
        
    Returns:
        Normalized phone number for database storage
    """
    return normalize_phone(old_phone) or old_phone