"""
Test Phone Normalization Service
================================
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from server.services.phone_service import (
    normalize_phone,
    get_phone_variants,
    format_phone_display,
    validate_us_phone
)


def test_normalize_phone():
    """Test phone normalization with various formats."""
    
    # Test cases: (input, expected_output)
    test_cases = [
        # 10-digit formats
        ("2125551234", "+12125551234"),
        ("(212) 555-1234", "+12125551234"),
        ("212-555-1234", "+12125551234"),
        ("212.555.1234", "+12125551234"),
        ("212 555 1234", "+12125551234"),
        
        # 11-digit formats with country code
        ("12125551234", "+12125551234"),
        ("1-212-555-1234", "+12125551234"),
        ("+12125551234", "+12125551234"),
        ("+1 212 555 1234", "+12125551234"),
        ("1 (212) 555-1234", "+12125551234"),
        
        # Edge cases
        ("", None),
        (None, None),
        ("123", None),  # Too short
        ("123456789012", None),  # Too long
        ("02125551234", None),  # Invalid US format (starts with 0)
    ]
    
    print("Testing normalize_phone():")
    print("-" * 50)
    
    passed = 0
    failed = 0
    
    for input_phone, expected in test_cases:
        result = normalize_phone(input_phone)
        status = "✅" if result == expected else "❌"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
            
        print(f"{status} Input: '{input_phone}' → Expected: '{expected}', Got: '{result}'")
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_get_phone_variants():
    """Test getting phone variants for migration."""
    
    print("\nTesting get_phone_variants():")
    print("-" * 50)
    
    test_phones = [
        "2125551234",
        "+12125551234",
        "12125551234",
    ]
    
    for phone in test_phones:
        variants = get_phone_variants(phone)
        print(f"Input: '{phone}'")
        print(f"Variants: {variants}")
        print()
    
    return True


def test_format_phone_display():
    """Test phone formatting for display."""
    
    print("\nTesting format_phone_display():")
    print("-" * 50)
    
    test_cases = [
        ("+12125551234", "(212) 555-1234"),
        ("2125551234", "(212) 555-1234"),
        ("12125551234", "(212) 555-1234"),
        ("invalid", "invalid"),  # Should return as-is
    ]
    
    passed = 0
    failed = 0
    
    for input_phone, expected in test_cases:
        result = format_phone_display(input_phone)
        status = "✅" if result == expected else "❌"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
            
        print(f"{status} Input: '{input_phone}' → Expected: '{expected}', Got: '{result}'")
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


def test_validate_us_phone():
    """Test US phone validation."""
    
    print("\nTesting validate_us_phone():")
    print("-" * 50)
    
    test_cases = [
        ("2125551234", True),      # Valid 10-digit
        ("+12125551234", True),    # Valid with country code
        ("12125551234", True),     # Valid 11-digit
        ("0125551234", False),     # Invalid area code (starts with 0)
        ("1125551234", False),     # Invalid area code (starts with 1)
        ("2120551234", False),     # Invalid exchange (starts with 0)
        ("2121551234", False),     # Invalid exchange (starts with 1)
        ("123", False),            # Too short
        ("", False),               # Empty
    ]
    
    passed = 0
    failed = 0
    
    for input_phone, expected in test_cases:
        result = validate_us_phone(input_phone)
        status = "✅" if result == expected else "❌"
        
        if result == expected:
            passed += 1
        else:
            failed += 1
            
        print(f"{status} Input: '{input_phone}' → Expected: {expected}, Got: {result}")
    
    print(f"\nResults: {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    print("=" * 60)
    print("PHONE SERVICE TEST SUITE")
    print("=" * 60)
    
    all_passed = True
    
    all_passed &= test_normalize_phone()
    all_passed &= test_get_phone_variants()
    all_passed &= test_format_phone_display()
    all_passed &= test_validate_us_phone()
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED - Please review above")
    print("=" * 60)