# Server Refactor Documentation

## Problem Statement
Critical cross-user data contamination issue discovered where users were seeing other users' cart data. Root cause was phone number format mismatches and complex fallback logic. Additionally, server.py had grown to 2000+ lines making it difficult to maintain.

## Solution Approach

### 1. Phone Normalization Service
Created centralized phone service to ensure consistent E.164 format (+1XXXXXXXXXX) across the entire system.

**Key Functions:**
- `normalize_phone()`: Converts any phone format to E.164
- `get_phone_variants()`: Returns all possible formats for database lookups
- `format_phone_display()`: Formats for user display (XXX) XXX-XXXX
- `validate_us_phone()`: Validates US phone numbers

**Location:** `/server/services/phone_service.py`

### 2. Service Extraction Pattern
Broke up monolithic server.py into logical services while keeping routes in main file.

**Services Created:**
- `phone_service.py` - Phone number handling (60 lines)
- `sms_handler.py` - SMS routing and formatting (131 lines)  
- `meal_generator.py` - GPT meal generation (240 lines)
- `cart_service.py` - Cart analysis and scraping (115 lines)

**Benefits:**
- Reduced server.py from 2000+ to ~1600 lines
- Clear separation of concerns
- Easier testing and debugging
- Reusable components

### 3. Implementation Details

#### Phone Normalization Integration
All database operations now use normalized phone numbers:
```python
# Before (caused data bleeding):
phone_variants = [phone, f"+{phone}", f"+1{phone}", f"1{phone}"]
for variant in phone_variants:
    user = db.get_user_by_phone(variant)
    
# After (consistent format):
normalized_phone = normalize_phone(phone)
user = db.get_user_by_phone(normalized_phone)
```

#### Service Usage in Routes
Routes remain in server.py but delegate to services:
```python
# Before (200+ lines in route):
@app.post("/api/refresh-meals")
async def refresh_meals(request: Request):
    # 200+ lines of meal generation logic
    
# After (15 lines):
@app.post("/api/refresh-meals")
async def refresh_meals(request: Request):
    from services.meal_generator import generate_meals
    result = await generate_meals(cart_data, preferences)
    return result
```

## Critical Fixes Applied

1. **Phone Format Collisions:** Eliminated by using single normalized format
2. **Cart Lock Fallback:** Removed aggressive fallback that used wrong user's data
3. **Database Lookups:** Now use consistent phone format preventing mismatches
4. **Error Handling:** Services have proper error boundaries

## Testing Results
- ✅ Phone service: All 33 tests passing
- ✅ Server startup: No syntax errors
- ✅ Meal generation: Working with user preferences
- ✅ SMS routing: Properly delegated to handler

## Future Improvements
1. Move routes to separate files when ready for full MVC
2. Add Redis caching layer for cart data
3. Implement proper session management
4. Add comprehensive logging

## Migration Notes
When updating production:
1. Ensure all phone numbers in database are normalized
2. Run phone migration script if needed
3. Test with various phone formats
4. Monitor for any format-related errors

## File Structure
```
server/
├── server.py (1600 lines - routes and orchestration)
├── services/
│   ├── phone_service.py (phone normalization)
│   ├── sms_handler.py (SMS message routing)
│   ├── meal_generator.py (GPT meal generation)
│   └── cart_service.py (cart analysis)
└── ...other files
```

This refactor maintains functionality while improving maintainability and fixing the critical data contamination bug.