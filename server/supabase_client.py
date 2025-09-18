"""
Supabase client helper for storing and retrieving user records.

Environment variables required:
- SUPABASE_URL
- SUPABASE_KEY  (service_role recommended for server-side use)

This module intentionally keeps a minimal API so the rest of the codebase
can call a single place for database access.
"""

from __future__ import annotations

import os
import base64
from typing import Optional, Dict, Any

# More explicit .env loading
from dotenv import load_dotenv
from pathlib import Path
env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)


from supabase import create_client, Client


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


def get_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError(
            "Missing SUPABASE_URL or SUPABASE_KEY in environment."
        )
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def _encode_password(plain_text: str) -> str:
    """Secure password encryption using Fernet.

    This replaces the insecure base64 encoding with proper
    symmetric encryption using cryptography library.
    """
    if plain_text is None:
        return ""
    
    try:
        from services.encryption_service import PasswordEncryption
        return PasswordEncryption.encrypt_password(plain_text)
    except ImportError:
        # Fallback to base64 if encryption service not available
        print("⚠️ Using fallback base64 encoding - encryption service not available")
        return base64.b64encode(plain_text.encode("utf-8")).decode("ascii")


def _decode_password(encoded_text: str) -> str:
    """Decrypt password using proper encryption.
    
    Handles both new Fernet encryption and legacy base64 encoding
    for backward compatibility during migration.
    """
    if not encoded_text:
        return ""
    
    try:
        from services.encryption_service import PasswordEncryption
        decrypted = PasswordEncryption.decrypt_password(encoded_text)
        return decrypted if decrypted else encoded_text
    except ImportError:
        # Fallback to base64 if encryption service not available
        try:
            return base64.b64decode(encoded_text.encode("ascii")).decode("utf-8")
        except Exception:
            return encoded_text


def upsert_user_credentials(
    *, phone_number: Optional[str], ftp_email: str, ftp_password: str, preferences: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Insert or update a user row keyed by phone_number or email.

    Either phone_number or ftp_email must be provided. If both are provided,
    we upsert on ftp_email priority and include phone_number.
    """
    if not ftp_email:
        raise ValueError("ftp_email is required")

    client = get_client()
    encoded_pw = _encode_password(ftp_password or "")

    # Prefer upsert on ftp_email since SMS may change, email is stable for FTP.
    payload = {
        "phone_number": phone_number,
        "ftp_email": ftp_email,
        "ftp_password_encrypted": encoded_pw,
        "preferences": preferences or {},
    }

    # Upsert based on unique key behavior. The supabase-py upsert uses the
    # table's unique constraints to determine conflict. Ensure ftp_email is unique.
    res = (
        client.table("users")
        .upsert(payload, on_conflict="ftp_email")
        .execute()
    )
    return res.data[0] if res.data else {}


def get_user_by_phone(phone_number: str) -> Optional[Dict[str, Any]]:
    client = get_client()
    
    # Try multiple phone formats to handle inconsistencies
    phone_formats = []
    
    # If it starts with +1, also try without it
    if phone_number.startswith('+1'):
        phone_formats.append(phone_number)  # +14254955323
        phone_formats.append(phone_number[2:])  # 4254955323
    # If it doesn't start with +1, also try with it  
    elif len(phone_number) == 10 and phone_number[0] != '1':
        phone_formats.append(phone_number)  # 4254955323
        phone_formats.append(f'+1{phone_number}')  # +14254955323
    else:
        phone_formats.append(phone_number)
    
    # Try each format
    for phone_format in phone_formats:
        res = (
            client.table("users")
            .select("id, phone_number, ftp_email, ftp_password_encrypted, preferences")
            .eq("phone_number", phone_format)
            .limit(1)
            .execute()
        )
        if res.data:
            row = res.data[0]
            row["ftp_password"] = _decode_password(row.get("ftp_password_encrypted", ""))
            return row
    
    # No user found with any format
    return None


def get_user_by_email(ftp_email: str) -> Optional[Dict[str, Any]]:
    client = get_client()
    res = (
        client.table("users")
        .select("id, phone_number, ftp_email, ftp_password_encrypted, preferences")
        .eq("ftp_email", ftp_email)
        .limit(1)
        .execute()
    )
    if not res.data:
        return None
    row = res.data[0]
    row["ftp_password"] = _decode_password(row.get("ftp_password_encrypted", ""))
    return row


def update_user_preferences(phone_number: str, preferences: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Update only the preferences for a user, without touching credentials.

    Args:
        phone_number: User's phone number
        preferences: Updated preferences dictionary

    Returns:
        Updated user record or None if update failed
    """
    client = get_client()

    # Try multiple phone formats
    phone_formats = []
    if phone_number.startswith('+1'):
        phone_formats.append(phone_number)
        phone_formats.append(phone_number[2:])
    elif len(phone_number) == 10 and phone_number[0] != '1':
        phone_formats.append(phone_number)
        phone_formats.append(f'+1{phone_number}')
    else:
        phone_formats.append(phone_number)

    # Try each format to find and update user
    for phone_format in phone_formats:
        try:
            res = (
                client.table("users")
                .update({"preferences": preferences})
                .eq("phone_number", phone_format)
                .execute()
            )
            if res.data:
                return res.data[0]
        except Exception as e:
            continue

    return None


def save_latest_cart_data(phone_number: str, cart_data: Dict[str, Any], delivery_date = None, meal_suggestions = None) -> bool:
    """
    Save latest cart data for a user (overwrites previous data).
    
    Args:
        phone_number: User's phone number
        cart_data: Complete cart data from scraper
        delivery_date: Optional delivery date (datetime object, ISO string, or raw text)
        meal_suggestions: Optional meal suggestions from AI analysis
        
    Returns:
        True if successful, False otherwise
    """
    try:
        client = get_client()
        
        # Parse delivery date if it's messy text
        clean_delivery_date = None
        if delivery_date:
            clean_delivery_date = _parse_delivery_date(delivery_date)
        
        # Use upsert to overwrite existing data
        payload = {
            "phone_number": phone_number,
            "cart_data": cart_data,
            "scraped_at": "NOW()"
        }
        
        # Only add delivery_date if we have a clean one
        if clean_delivery_date:
            payload["delivery_date"] = clean_delivery_date
        
        # Add meal suggestions if provided
        if meal_suggestions:
            payload["meal_suggestions"] = meal_suggestions
        
        result = client.table("latest_cart_data").upsert(payload).execute()
        
        print(f"✅ Saved cart data for {phone_number}")
        if clean_delivery_date:
            print(f"📅 Delivery date: {clean_delivery_date}")
        if meal_suggestions:
            print(f"🍽️ Saved {len(meal_suggestions)} meal suggestions")
        return True
        
    except Exception as e:
        print(f"❌ Failed to save cart data: {e}")
        return False


def _parse_delivery_date(date_input):
    """
    Parse delivery date from various formats into ISO timestamp.
    
    Args:
        date_input: Can be datetime object, ISO string, or messy Farm to People text
        
    Returns:
        ISO timestamp string with timezone, or None if parsing fails
    """
    if not date_input:
        return None
    
    try:
        from datetime import datetime
        import re
        
        # If it's already a datetime object
        if hasattr(date_input, 'isoformat'):
            return date_input.isoformat()
        
        # If it's a string, try to parse it
        date_str = str(date_input)
        
        # Check if it's already an ISO string
        if 'T' in date_str and ('Z' in date_str or '+' in date_str or '-' in date_str[-6:]):
            return date_str
        
        # Parse messy Farm to People text like "AboutProducers...Shopping for: Sun, Aug 31, 10:00AM..."
        pattern = r'(Sun|Mon|Tue|Wed|Thu|Fri|Sat)\w*,?\s+(\w+)\s+(\d+)'
        match = re.search(pattern, date_str)
        
        if match:
            day_abbr = match.group(1)  # Sun
            month_abbr = match.group(2)  # Aug  
            day_num = int(match.group(3))  # 31
            
            # Convert month abbreviation to number
            months = {
                'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
                'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12,
                'January': 1, 'February': 2, 'March': 3, 'April': 4, 
                'May': 5, 'June': 6, 'July': 7, 'August': 8, 
                'September': 9, 'October': 10, 'November': 11, 'December': 12
            }
            
            month_num = months.get(month_abbr)
            if month_num:
                current_year = datetime.now().year
                
                # Create delivery datetime (assume 2 PM ET for deliveries)
                delivery_dt = datetime(current_year, month_num, day_num, 14, 0, 0)
                
                # If the date is in the past, it's probably next year
                if delivery_dt < datetime.now():
                    delivery_dt = datetime(current_year + 1, month_num, day_num, 14, 0, 0)
                
                # Convert to ET timezone and return ISO format
                import pytz
                eastern = pytz.timezone('US/Eastern')
                delivery_et = eastern.localize(delivery_dt)
                return delivery_et.isoformat()
        
        print(f"⚠️ Could not parse delivery date: {date_str}")
        return None
        
    except Exception as e:
        print(f"⚠️ Error parsing delivery date: {e}")
        return None


def get_latest_cart_data(phone_number: str) -> Optional[Dict[str, Any]]:
    """
    Get stored cart data for a user.
    
    Returns:
        Dict with cart_data, delivery_date, scraped_at if found, None otherwise
    """
    try:
        client = get_client()
        
        # Try multiple phone formats to handle inconsistencies
        phone_formats = []
        
        # If it starts with +1, also try without it
        if phone_number.startswith('+1'):
            phone_formats.append(phone_number)  # +14254955323
            phone_formats.append(phone_number[2:])  # 4254955323
        # If it doesn't start with +1, also try with it
        elif len(phone_number) == 10 and phone_number[0] != '1':
            phone_formats.append(phone_number)  # 4254955323
            phone_formats.append(f'+1{phone_number}')  # +14254955323
        else:
            phone_formats.append(phone_number)
        
        # Try each format
        for phone_format in phone_formats:
            result = client.table("latest_cart_data").select("*").eq("phone_number", phone_format).execute()
            
            if result.data:
                stored_data = result.data[0]
                print(f"📦 Retrieved stored cart data for {phone_format} (scraped: {stored_data.get('scraped_at')})")
                return stored_data
        
        # No data found with any format
        print(f"⚠️ No stored cart data found for {phone_number} (tried: {', '.join(phone_formats)})")
        return None
            
    except Exception as e:
        print(f"❌ Failed to retrieve cart data: {e}")
        return None


# ==========================================
# SWAP HISTORY FUNCTIONS
# For tracking user cart changes and preventing ping-pong suggestions
# ==========================================

def save_swap_history(swap_data: Dict[str, Any]) -> bool:
    """
    Save a detected swap to the history table.

    Args:
        swap_data: Dict with phone, delivery_date, box_name, from_item, to_item

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        client = get_client()

        # Prepare the data for insertion
        insert_data = {
            'phone': swap_data['phone'],
            'delivery_date': swap_data['delivery_date'],
            'box_name': swap_data.get('box_name'),
            'from_item': swap_data['from_item'],
            'to_item': swap_data['to_item']
        }

        result = client.table('swap_history').insert(insert_data).execute()

        if result.data:
            print(f"✅ Saved swap: {swap_data['from_item']} → {swap_data['to_item']} for {swap_data['phone']}")
            return True
        else:
            print(f"⚠️ No data returned when saving swap")
            return False

    except Exception as e:
        print(f"❌ Failed to save swap history: {e}")
        return False


def get_swap_history(phone_number: str, delivery_date: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get recent swap history for a user and delivery date.

    Args:
        phone_number: User's phone number
        delivery_date: Delivery date (YYYY-MM-DD format)
        limit: Maximum number of swaps to return

    Returns:
        List of swap dictionaries with from_item, to_item, box_name, detected_at
    """
    try:
        client = get_client()

        # Handle multiple phone formats (consistent with other functions)
        phone_formats = [phone_number]
        if phone_number.startswith('+1'):
            phone_formats.append(phone_number[2:])  # Remove +1
        elif phone_number.startswith('1') and len(phone_number) == 11:
            phone_formats.append(phone_number[1:])  # Remove leading 1
        elif not phone_number.startswith('+'):
            phone_formats.append(f"+1{phone_number}")  # Add +1
            if phone_number.startswith('1'):
                phone_formats.append(f"+{phone_number}")  # Add just +

        # Try each phone format
        for phone_format in phone_formats:
            result = client.table('swap_history')\
                .select('*')\
                .eq('phone', phone_format)\
                .eq('delivery_date', delivery_date)\
                .order('detected_at', desc=True)\
                .limit(limit)\
                .execute()

            if result.data:
                print(f"📋 Retrieved {len(result.data)} swap records for {phone_format}")
                return result.data

        # No swaps found with any format
        print(f"📋 No swap history found for {phone_number} on {delivery_date}")
        return []

    except Exception as e:
        print(f"❌ Failed to get swap history: {e}")
        return []


def get_recent_swaps_for_phone(phone_number: str, days: int = 7, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Get all recent swaps for a user across all deliveries.

    Args:
        phone_number: User's phone number
        days: Number of days to look back
        limit: Maximum number of swaps to return

    Returns:
        List of swap dictionaries
    """
    try:
        client = get_client()

        # Calculate date threshold
        from datetime import datetime, timedelta
        threshold_date = datetime.now() - timedelta(days=days)

        # Handle multiple phone formats
        phone_formats = [phone_number]
        if phone_number.startswith('+1'):
            phone_formats.append(phone_number[2:])
        elif not phone_number.startswith('+'):
            phone_formats.append(f"+1{phone_number}")

        # Try each phone format
        for phone_format in phone_formats:
            result = client.table('swap_history')\
                .select('*')\
                .eq('phone', phone_format)\
                .gte('detected_at', threshold_date.isoformat())\
                .order('detected_at', desc=True)\
                .limit(limit)\
                .execute()

            if result.data:
                print(f"📋 Retrieved {len(result.data)} recent swaps for {phone_format}")
                return result.data

        return []

    except Exception as e:
        print(f"❌ Failed to get recent swaps: {e}")
        return []


