# Phone Service Documentation & Context

## Why This Service Exists

### The Problem We Solved
On September 1, 2025, we discovered a **critical data contamination bug** where users were seeing other users' cart data and meal suggestions. The root cause was inconsistent phone number formatting throughout the codebase.

### What Was Happening
1. **Multiple Format Attempts**: Every endpoint tried different phone formats:
   ```python
   # This pattern was repeated 6+ times in server.py alone:
   phone_formats = [phone, f"+{phone}", f"1{phone}", f"+1{phone}"]
   ```

2. **Format Collisions**: Different users' phones could match incorrectly:
   - User A: `2125551234` stored as `+12125551234`
   - User B: `125551234` (different area code)
   - System tries `1125551234` for User B, potentially matching wrong data

3. **Database Inconsistency**: Phone numbers were stored in various formats:
   - Some with `+1` prefix
   - Some with just `1` prefix
   - Some with no prefix
   - Made lookups unreliable

## The Solution: Centralized Phone Service

### Core Principle
**One source of truth for phone number handling**. Every phone number entering or leaving the system goes through this service.

### Standard Format
All phone numbers are normalized to **E.164 format**: `+1XXXXXXXXXX`
- Always starts with `+1` for US numbers
- Exactly 10 digits after country code
- No spaces, dashes, or parentheses

### Service Components

#### 1. `normalize_phone(phone: str) -> Optional[str]`
**Purpose**: Convert any phone format to our standard format.

**Why it matters**: Prevents format mismatches that caused user data to bleed across accounts.

**Example usage**:
```python
# Before (dangerous - could match wrong user):
user = db.get_user_by_phone(phone)  # What format is phone?

# After (safe - consistent format):
normalized = normalize_phone(phone)
user = db.get_user_by_phone(normalized)
```

#### 2. `get_phone_variants(phone: str) -> List[str]`
**Purpose**: Generate all possible formats that might exist in the database.

**Why it matters**: During migration period, we need to find records stored with old formats.

**Context**: We can't instantly migrate all existing data, so this helps during transition.

**Example usage**:
```python
# Migration helper - find user with any old format
for variant in get_phone_variants(user_input):
    user = db.get_user_by_phone(variant)
    if user:
        # Migrate to normalized format
        db.update_user_phone(user.id, normalize_phone(variant))
        break
```

#### 3. `format_phone_display(phone: str) -> str`
**Purpose**: Format normalized phones for user-friendly display.

**Why it matters**: Users expect to see `(212) 555-1234`, not `+12125551234`.

**Example usage**:
```python
# Show phone in UI
user_phone = normalize_phone(input)  # Store as +12125551234
display_phone = format_phone_display(user_phone)  # Show as (212) 555-1234
```

#### 4. `validate_us_phone(phone: str) -> bool`
**Purpose**: Validate that a phone number is a legitimate US number.

**Why it matters**: Prevents invalid data from entering the system.

**Validation rules**:
- Must be 10 digits (or 11 with country code)
- Area code can't start with 0 or 1
- Exchange can't start with 0 or 1
- Must be normalizable to our standard format

## Implementation Strategy

### Phase 1: Create Service (COMPLETE)
- ✅ Built centralized phone service
- ✅ Added comprehensive tests
- ✅ Documented context and reasoning

### Phase 2: Update Critical Paths (IN PROGRESS)
1. **User Authentication** (`/analyze-cart`, `/onboard`)
   - These are the most critical for preventing cross-contamination
   
2. **Cart Scraping** (comprehensive_scraper.py)
   - Must store with normalized phone
   
3. **Database Operations** (supabase_client.py)
   - All lookups use normalized format

### Phase 3: Migration & Cleanup
1. **Database Migration Script**
   - Normalize all existing phone numbers
   - Add unique constraint on normalized format
   
2. **Remove Old Logic**
   - Delete all `phone_formats = [...]` patterns
   - Replace with single `normalize_phone()` call

## Critical Code Locations to Update

### High Priority (Data Contamination Risk)
- `server.py:1260-1290` - analyze-cart phone lookup
- `server.py:268-273` - SMS flow phone lookup  
- `supabase_client.py:246-267` - get_latest_cart_data
- `comprehensive_scraper.py:681` - Cart data storage

### Medium Priority (Functionality)
- `server.py:1984-2000` - Settings lookup
- `server.py:1439-1444` - Preferences lookup
- `meal_planning_api.py:332-337` - Meal plan generation

### Low Priority (Cleanup)
- Remove all `phone_formats` list comprehensions
- Standardize error messages for invalid phones

## Testing Checklist

Before deploying phone service integration:

- [ ] Test with US phone numbers in various formats
- [ ] Test with international numbers (should reject gracefully)
- [ ] Test with invalid numbers (too short/long)
- [ ] Test multi-user scenario (critical!)
- [ ] Test with existing database records
- [ ] Test migration of old formats

## Rollback Plan

If issues arise after deployment:

1. **Immediate**: Revert to previous commit
2. **Data Fix**: Run variants lookup as fallback
3. **Monitoring**: Check for failed lookups in logs

## Success Metrics

After full implementation:
- Zero cross-user data contamination incidents
- Consistent phone format in database
- Reduced code complexity (one place for phone logic)
- Easier debugging (predictable format)

## Lessons Learned

1. **Never trust user input format** - Always normalize
2. **One source of truth** - Don't repeat logic
3. **Migration strategy** - Can't break existing data
4. **Test multi-user scenarios** - Critical for SaaS
5. **Document the "why"** - Future developers need context

---

*Created: September 1, 2025*  
*Context: Critical fix for cross-user data contamination bug*  
*Author: System refactoring to prevent future incidents*