# Services Directory

This directory contains extracted business logic services from the main server.py file. Each service handles a specific domain of functionality.

## Services Overview

### phone_service.py
**Purpose:** Centralized phone number handling to prevent cross-user data contamination

**Key Functions:**
- `normalize_phone(phone: str) -> Optional[str]` - Converts to E.164 format (+1XXXXXXXXXX)
- `get_phone_variants(phone: str) -> List[str]` - Returns all possible formats for lookups
- `format_phone_display(phone: str) -> str` - Formats as (XXX) XXX-XXXX for display
- `validate_us_phone(phone: str) -> bool` - Validates US phone numbers

**Usage:**
```python
from services.phone_service import normalize_phone

normalized = normalize_phone("(212) 555-1234")  # Returns: "+12125551234"
```

### sms_handler.py
**Purpose:** SMS message routing and formatting

**Key Functions:**
- `route_sms_message(phone: str, message: str) -> tuple[str, bool]` - Routes SMS to handlers
- `format_sms_with_help(message: str, state: str) -> str` - Adds contextual help text

**Usage:**
```python
from services.sms_handler import route_sms_message

response, trigger_background = route_sms_message("+12125551234", "plan")
```

### meal_generator.py
**Purpose:** GPT-based meal plan generation from cart data

**Key Functions:**
- `generate_meals(cart_data: Dict, preferences: Dict) -> Dict` - Main generation endpoint
- `extract_ingredients_from_cart(cart_data: Dict) -> Dict` - Categorizes ingredients
- `build_meal_prompt(ingredients: Dict, preferences: Dict) -> str` - Creates GPT prompt

**Usage:**
```python
from services.meal_generator import generate_meals

result = await generate_meals(cart_data, user_preferences)
meals = result["meals"]
```

### cart_service.py
**Purpose:** Cart analysis and Farm to People scraping

**Key Functions:**
- `analyze_user_cart(phone: str, use_mock: bool) -> Dict` - Gets and analyzes cart

**Usage:**
```python
from services.cart_service import analyze_user_cart

cart_result = await analyze_user_cart("+12125551234")
cart_data = cart_result["cart_data"]
```

## Design Principles

1. **Single Responsibility:** Each service handles one domain
2. **Consistent Interfaces:** All return Dict with success/error keys
3. **Error Handling:** Services catch and return errors gracefully
4. **No Side Effects:** Services don't modify global state
5. **Testable:** Each service can be tested independently

## Adding New Services

When creating a new service:
1. Create a new file in this directory
2. Import only what's needed
3. Return consistent Dict format: `{"success": bool, "data": any, "error": str}`
4. Add error handling
5. Document functions
6. Create tests in `/tests/test_<service_name>.py`

## Dependencies

Services can import from:
- Standard library
- Project dependencies (openai, supabase, etc.)
- Other services (sparingly)
- Parent modules (db, scrapers)

Avoid circular imports by keeping dependencies minimal.

## Testing

Run service tests:
```bash
python tests/test_phone_service.py
python tests/test_meal_generator.py  # TODO: Create this
python tests/test_sms_handler.py     # TODO: Create this
```

## Migration Status

- ✅ Phone handling logic
- ✅ SMS routing and formatting
- ✅ Meal generation (240+ lines)
- ✅ Cart analysis basics
- ⏳ User preferences (partially in onboarding.py)
- ⏳ PDF generation (in generators/)
- ⏳ Database operations (still in supabase_client.py)