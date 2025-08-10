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
    """Lightweight reversible encoding.

    NOTE: This is NOT cryptographic encryption. Replace with a KMS-based
    envelope encryption scheme for production. For now we avoid new
    dependencies and simply avoid storing cleartext.
    """
    if plain_text is None:
        return ""
    return base64.b64encode(plain_text.encode("utf-8")).decode("ascii")


def _decode_password(encoded_text: str) -> str:
    if not encoded_text:
        return ""
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
        .select("id, phone_number, ftp_email")
        .execute()
    )
    return res.data[0] if res.data else {}


def get_user_by_phone(phone_number: str) -> Optional[Dict[str, Any]]:
    client = get_client()
    res = (
        client.table("users")
        .select("id, phone_number, ftp_email, ftp_password_encrypted, preferences")
        .eq("phone_number", phone_number)
        .limit(1)
        .execute()
    )
    if not res.data:
        return None
    row = res.data[0]
    row["ftp_password"] = _decode_password(row.get("ftp_password_encrypted", ""))
    return row


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


