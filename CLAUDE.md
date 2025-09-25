# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🎯 PROJECT OVERVIEW

**Farm to People AI Assistant** transforms weekly produce boxes into personalized meal plans through intelligent cart scraping and AI-powered meal generation. Users complete onboarding, connect their Farm to People accounts, and receive meal suggestions based on their actual cart contents and preferences.

**Live URL:** https://farmtopeople-production.up.railway.app
**Branch:** `feature/customer-automation`
**Status:** Production ready with recent mobile UI fixes (Sept 2025)

---

## 🚀 ESSENTIAL DEVELOPMENT COMMANDS

### **Initial Setup (One-Time)**
```bash
# Clone and setup
git clone https://github.com/zoelsner/farmtopeople.git
cd farmtopeople
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
playwright install chromium  # Required for cart scraping

# Environment setup
cp .env.example .env  # Edit with your credentials
```

### **Daily Development Workflow**
```bash
# Activate environment (ALWAYS REQUIRED)
source venv/bin/activate

# Start server
python server/server.py

# Test critical paths
cd scrapers && python comprehensive_scraper.py  # Test cart scraping
curl http://localhost:8000/api/get-saved-cart?phone=YOUR_PHONE  # Test API

# Open application
open http://localhost:8000/onboard  # Start onboarding flow
open http://localhost:8000/dashboard  # Main dashboard
```

### **Process Management**
```bash
# Find server process
ps aux | grep "python.*server.py" | grep -v grep

# Kill server by PID
kill [PID]

# Check port usage
lsof -i :8000

# Check Redis (if running locally)
redis-cli ping
```

### **Debugging Commands**
```bash
# Test phone number lookup (most common issue)
python -c "
import sys; sys.path.insert(0, 'server')
import supabase_client as db
from services.phone_service import normalize_phone
phone = 'YOUR_PHONE_NUMBER'
normalized = normalize_phone(phone)
user = db.get_user_by_phone(normalized)
print(f'Normalized: {normalized}')
print(f'User found: {bool(user)}')"

# Check Redis cache
python -c "
import sys; sys.path.insert(0, 'server')
from services.cache_service import CacheService
phone = 'YOUR_PHONE_NUMBER'
cart = CacheService.get_cart(phone)
meals = CacheService.get_meals(phone)
print(f'Cached cart: {bool(cart)}')
print(f'Cached meals: {len(meals) if meals else 0}')"
```

---

## 🧠 DECISION-MAKING PRINCIPLES

### **Confidence-Based Problem Solving**
After the loading screen bug that took 70+ attempts, we learned the importance of evidence-based investigation:

- **80-85% confidence**: Good for most decisions and implementations
- **95% confidence**: Required when repeatedly failing (3+ attempts) or debugging complex issues
- **Research first**: Use internet when knowledge might be dated or uncertain
- **Evidence over assumptions**: "More research is never a bad thing"

### **When to Escalate Confidence Requirements**
- After 3+ failed attempts → increase to 90% confidence
- After 5+ failed attempts → demand 95% confidence
- Complex architectural decisions → start at 85% minimum
- Production-breaking bugs → always require 95%

### **Research-First Approach**
From the loading screen bug experience (70+ attempts before success):
1. **Gather ALL data** - Console logs, server logs, network responses
2. **Verify assumptions** - Test each component individually
3. **Check both sides** - Server AND client can have issues simultaneously
4. **Document thoroughly** - Create CRITICAL_LESSONS files for major fixes

### **Model Selection (2025)**
**Current Choice: GPT-5 Mini with low reasoning**
- **Why**: 6x fewer hallucinations than GPT-4o (4.8% vs 20.6%)
- **Config**: 8K output tokens for meals, 2K for single meals
- **Reasoning**: "low" level balances accuracy with speed
- **Token allocation**: 50K input accommodates full context
- **Fallback**: GPT-4o available for simple/fast tasks

### **Internet Research Policy**
Use web search when:
- Comparing AI models or services (capabilities change rapidly)
- Checking latest API features/pricing
- Verifying best practices (frameworks evolve)
- Debugging unusual patterns that don't match known issues
- Confirming third-party service details or limitations

### **Git Workflow Strategy**
From this deployment experience:
- **Daily work**: `feature/customer-automation` (all iterations and debugging)
- **Production**: `main` branch (stable milestones only)
- **Commit philosophy**: Feature branch shows the journey, main shows destinations
- **Merge strategy**: Squash feature work into comprehensive main commits

### **Feature Development Philosophy**
"I really don't want feature creep" - Focus on:
- **Core value adds** that AI uniquely enables
- **Strategic additions** (smart swaps) over complex systems (pantry tracking)
- **Direct cart value** - helps users maximize their FarmToTable investment
- **"What this enables"** messaging over feature lists

---

## 🏗️ HIGH-LEVEL ARCHITECTURE

### **Service Layer (12 Modular Services)**
```
server/services/
├── phone_service.py       # E.164 normalization (CRITICAL for data isolation)
├── cache_service.py       # Redis with 2hr TTL for cart, 24hr for meals
├── meal_generator.py      # GPT-5 Mini integration with low reasoning
├── cart_service.py        # Cart analysis orchestration
├── encryption_service.py  # Fernet encryption for FTP credentials
├── account_service.py     # User lookup and management
├── scraper_service.py     # Browser automation coordination
├── sms_handler.py         # Vonage SMS routing
├── meal_flow_service.py   # Complete meal generation flow
├── data_isolation_service.py  # User data separation
├── notification_service.py   # SMS notifications
└── pdf_service.py         # Recipe PDF generation
```

### **Frontend Architecture (Monolithic Challenge)**
- **dashboard.html**: 4094 lines containing ALL frontend logic
- **Two `updateMealSuggestions()` functions**: Line 3089 is the active one (Line 2713 is orphaned)
- **State Management Pattern**: Unified classList + style.display usage
- **PWA Navigation**: iframe modal pattern for Settings to prevent page refresh

### **Data Flow Architecture**
```
Phone Input → E.164 Normalization → Supabase Query → Redis Check → Database Fallback
Cart Scrape → Redis Cache (2hr TTL) → Frontend State → Both Tabs Update
User Action → Service Layer → Cache Update → Real-time Frontend Sync
```

### **Critical Patterns**

#### **Phone Number Normalization (Most Common Debug Issue)**
```python
# System tries these formats in order to prevent "user not found" errors:
normalized_phone = normalize_phone(phone)  # → +14254955323
variants = [phone, f"+{phone}", f"+1{phone}", f"1{phone}"]
# All data lookups MUST use normalized phone to prevent cross-user contamination
```

#### **Cache-First Strategy**
```python
# Pattern: Always check Redis before database/API calls
cached_response = CacheService.get_cart_response(phone)
if cached_response and not force_refresh:
    return cached_response
# Fallback preserves swaps/addons/meals during cart lock scenarios
```

#### **Dynamic DOM Management (Recent Fix)**
```javascript
// Pattern: Create missing containers dynamically
let grid = document.getElementById('mealSuggestionsGrid');
if (!grid) {
    grid = document.createElement('div');
    grid.id = 'mealSuggestionsGrid';
    container.appendChild(grid);
}
```

---

## 🔧 CRITICAL BUSINESS RULES

### **Cart Lock Logic**
- Carts lock at **11:59 AM ET the day before delivery**
- Thursday delivery → Wednesday 11:59 AM lock
- System falls back to cached cart data during lock period
- **Known Issue**: Date calculation shows wrong day (Sun instead of Wed)

### **Protein Requirements**
- Women: 30g minimum per meal
- Men: 35-40g minimum per meal
- Protein content is displayed in meal cards (not in meal titles)

### **Meal Categorization**
- **Snacks**: <20 minutes cooking time + specific ingredients (yogurt, fruit, nuts)
- **Meals**: Everything else
- **Parsing Bug Fixed**: "10-12 min" was parsed as 1012 minutes - now uses `time_part.split('-')[0]`

### **Data Architecture**
- **Phone numbers**: E.164 format (+14254955323) for all storage and lookups
- **Redis TTLs**: Cart data (2 hours), Meal data (24 hours)
- **GPT Model**: Always use GPT-5, never GPT-3.5

---

## 🚨 KNOWN ARCHITECTURAL DEBT

### **High Priority Issues**
1. **dashboard.html Monolith**: 4094 lines, all frontend logic in one file
   - Contains duplicate functions
   - State management scattered throughout
   - Difficult to maintain and debug

2. **Missing Test Suite**: No pytest files, no automated testing
   - All testing is manual through browser
   - High risk of regressions

3. **Scraper Performance**: Takes 40-50 seconds (target: 25 seconds)
   - Playwright automation is slow
   - Multiple page loads and waits

### **Medium Priority Issues**
1. **Cart Lock Time Calculation**: Shows wrong day and disappears on refresh
2. **Mobile UI Scaling**: Recent fixes applied but needs ongoing attention
3. **Redis Dependency**: No graceful degradation when Redis unavailable

---

## 📱 RECENT CRITICAL FIXES (September 2025)

### **Mobile UI Fixes**
- Added `<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">`
- Updated CSS with `padding-bottom: calc(80px + env(safe-area-inset-bottom))`
- Fixed bottom navigation being cut off on mobile devices

### **Meals Tab Display Fixes**
- Fixed `renderMealSuggestions()` to dynamically create missing `mealSuggestionsGrid`
- Fixed `showMealLoadingState()` to preserve container structure
- Eliminated "Loading Meal Suggestions forever" issue

### **State Management Fixes**
- Unified classList and style.display usage patterns
- Fixed blank screen during cart refresh operations
- Enhanced loading animations and progress indicators

### **Cache Fallback Fixes**
- Preserve swaps/addons/meals during cart lock scenarios
- Complete data structure integrity in Redis fallbacks
- Proper cache response handling

---

## 🔍 DEBUGGING PATTERNS

### **Phone Number Issues (90% of "Data Not Found" Problems)**
```bash
# Symptoms: "User not found", old cart data, failed analysis
# Quick fix: Check if phone normalization is working
python -c "from server.services.phone_service import normalize_phone; print(normalize_phone('YOUR_PHONE'))"
```

### **State Management Issues**
```javascript
// Check if multiple sections are active (should never happen)
console.log({
    start: !startSection.style.display || startSection.style.display !== 'none',
    loading: !loadingSection.style.display || loadingSection.style.display !== 'none',
    cart: !cartSection.style.display || cartSection.style.display !== 'none'
});
// Only one should be true
```

### **Cache Issues**
```bash
# Check Redis cache status
python -c "
from server.services.cache_service import CacheService
response = CacheService.get_cart_response('PHONE')
print('Cache exists:', bool(response))
if response: print('Cache type:', response.get('cache_type'))"
```

---

## 🌍 ENVIRONMENT VARIABLES

```bash
# Farm to People Credentials (Required)
EMAIL=your.email@domain.com          # or FTP_EMAIL
PASSWORD=your_ftp_password           # or FTP_PWD

# AI Services (Required)
OPENAI_API_KEY=sk-...                # GPT-5 access (NOT GPT-3.5!)

# Database (Required)
SUPABASE_URL=https://...
SUPABASE_KEY=eyJ...

# SMS Service (Required)
VONAGE_API_KEY=...
VONAGE_API_SECRET=...
VONAGE_PHONE_NUMBER=18334391183

# Caching (Optional - falls back to memory)
REDIS_URL=redis://localhost:6379
```

---

## 📁 KEY FILE LOCATIONS

### **Main Application Files**
- `server/server.py` - FastAPI main application (1700+ lines)
- `server/templates/dashboard.html` - Frontend monolith (4094 lines)
- `scrapers/comprehensive_scraper.py` - Cart scraping logic
- `server/supabase_client.py` - Database operations

### **Configuration Files**
- `requirements.txt` - Python dependencies
- `.env` - Environment variables (copy from .env.example)
- `database/meal_planning_schema.sql` - Database schema

### **Documentation**
- `docs/archive/CLAUDE_v5.4.0_2025-09-17.md` - Previous detailed CLAUDE.md
- `MOBILE_UI_MEALS_TAB_FIXES_SUMMARY.md` - Recent fixes documentation
- `CRITICAL_FIXES_SESSION_SUMMARY.md` - Historical fixes

---

## 🎯 DEVELOPMENT PRIORITIES

### **When Making Changes**
1. **Always test cart scraping** with `python scrapers/comprehensive_scraper.py`
2. **Always activate venv** before running Python commands
3. **Check phone normalization** for any user data issues
4. **Test mobile UI** - recent fixes require ongoing validation
5. **Monitor Redis cache** - critical for performance

### **Common Gotchas**
- Don't assume GPT-3.5 - use GPT-5 only
- Don't modify phone numbers without normalization
- Don't break PWA navigation - Settings must use iframe pattern
- Don't ignore Redis TTL - cache expiration affects user experience
- Don't trust line numbers in dashboard.html - file changes frequently

### **Testing Approach**
- Manual testing through browser (no automated tests)
- Use real Farm to People accounts for comprehensive testing
- Test both mobile and desktop experiences
- Verify cart lock fallback scenarios

---

---

## 🚀 FUTURE FEATURE IDEAS

### **"Level Up" Add-Ons Gamification**
**Concept:** Transform add-ons from utilitarian "don't forget" lists into exciting meal enhancements

Instead of "You need these items", present as:
- "🎯 Level Up Your Tacos" → adds cilantro, lime, hot sauce ($4.99)
- "⭐ Level Up Again!" → adds avocado, sour cream ($3.99)
- "🚀 Max Level" → adds specialty cheese, pickled jalapeños ($5.99)

**Benefits:**
- Positive framing - enhancing, not missing
- Gamification appeals to achievement mindset
- Progressive levels of enhancement
- Reduces purchase pressure (feels optional)
- Makes grocery planning fun

**UI Concept:**
```
Your Meal: Chicken Tacos
━━━━━━━━━━━━━━━━━━━━━━
Base Level ✅ (you have everything needed)

[🎯 LEVEL UP! +$4.99]
Add: Fresh cilantro, lime, hot sauce
"Take your tacos from good to amazing!"
```

**Implementation Ideas:**
- Different level-up packages per meal type
- Track which users frequently "level up"
- Show "achievement unlocked" animations
- Seasonal level-ups (holiday herbs, summer fruits)
- Progressive disclosure (show next level after current)

---

**Last Updated:** September 24, 2025
**Version:** 6.1.0 (Added Future Features & Swap Detection Improvements)
**Archived Previous Version:** `docs/archive/CLAUDE_v5.4.0_2025-09-17.md`