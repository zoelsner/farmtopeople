# 🤖 CLAUDE.md - Farm to People AI Assistant Development Guide

## 🎯 PROJECT OVERVIEW

**Farm to People AI Assistant** transforms weekly produce boxes into personalized meal plans through intelligent SMS conversations. The system learns user preferences, analyzes cart contents, and delivers actionable cooking guidance.

**Current Status:** In Development - Meal calendar architecture complete, implementing frontend  
**Last Updated:** August 31, 2025  
**Version:** 3.0.0-beta (Meal Calendar Update)  
**Branch:** `feature/customer-automation`  
**Primary Contact:** SMS `18334391183` (Vonage)  
**Live URL:** https://farmtopeople-production.up.railway.app

---

## 🚀 QUICK START

### **Test the System**
```bash
# 1. Production Web App (LIVE)
open https://farmtopeople-production.up.railway.app/onboard

# 2. Local Development
source venv/bin/activate
python server/server.py
open http://localhost:8000/onboard

# 3. Test cart scraping with real data
cd scrapers && python comprehensive_scraper.py

# 4. Dashboard testing (requires onboarding first)
open http://localhost:8000/dashboard
```

### **Critical Development Rules**
- ✅ ALWAYS activate venv before running Python code
- ✅ Use GPT-5 (model="gpt-5") - it works in production!
- ✅ Test comprehensive_scraper.py before making changes
- ✅ Restart server after code modifications
- ✅ Best PDF design: `generators/templates/meal_plan_minimal.html` (Penny-style)
- ✅ **Protein in titles:** "38g protein" must be prominent under each meal name
- ✅ NEVER use GPT-3.5 - use GPT-5 or gpt-4o-mini only

---

## 📚 DOCUMENTATION INDEX

### **Business & Product Docs**
- [`docs/complete_business_flow.md`](docs/complete_business_flow.md) - End-to-end customer journey with confirmation flow
- [`docs/updated_business_flow.md`](docs/updated_business_flow.md) - Latest requirements (high-protein, meal calendar)
- [`docs/system_gap_analysis.md`](docs/system_gap_analysis.md) - Current gaps and improvement roadmap
- [`docs/ONBOARDING_SYSTEM.md`](docs/ONBOARDING_SYSTEM.md) - Preference collection implementation

### **Technical Documentation**
- [`docs/MEAL_CALENDAR_IMPLEMENTATION_PLAN.md`](docs/MEAL_CALENDAR_IMPLEMENTATION_PLAN.md) - **NEW:** Complete meal planning system design
- [`docs/CODEBASE_AUDIT_REPORT_AUG31.md`](docs/CODEBASE_AUDIT_REPORT_AUG31.md) - **NEW:** Comprehensive architecture audit
- [`database/meal_planning_schema.sql`](database/meal_planning_schema.sql) - **NEW:** Database schema for meal planning
- [`docs/refactoring_opportunities.md`](docs/refactoring_opportunities.md) - Architecture improvements & conversation state management
- [`docs/conversational_ai_architecture.md`](docs/conversational_ai_architecture.md) - AI system design patterns
- [`DEBUGGING_PROTOCOL.md`](DEBUGGING_PROTOCOL.md) - Scraper troubleshooting guide
- [`CRITICAL_SCRAPING_LESSONS_LEARNED.md`](CRITICAL_SCRAPING_LESSONS_LEARNED.md) - Historical failures & solutions

---

## 🏗️ SYSTEM ARCHITECTURE

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   WEB APP    │────▶│   DASHBOARD  │────▶│ MEAL CALENDAR│
│ (7-step flow)│     │ (Live Cart)  │     │ (Drag & Drop)│
└──────────────┘     └──────────────┘     └──────────────┘
        │                    │                     │
        ▼                    ▼                     ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   SUPABASE   │◀────│   SCRAPER    │────▶│ STORAGE LAYER│
│(Users+Meals) │     │ (Real Cart)  │     │ (Abstraction)│
└──────────────┘     └──────────────┘     └──────────────┘
        │                    │                     │
        ▼                    ▼                     ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   SESSIONS   │     │   AI MODELS  │     │    REDIS     │
│ (Cross-device)│     │  (GPT-5)     │     │  (Future)    │
└──────────────┘     └──────────────┘     └──────────────┘
```

---

## 🌐 PRIMARY WEB APP FLOW

### **7-Step Onboarding (Phone Number First)**
```
Step 1: Phone Number Entry
  ├─ Existing User? → Skip to Step 7 (FTP)
  └─ New User? → Continue to Step 2

Step 2: Household Size + Meal Timing
Step 3: Meal Preferences (pick 3+ dishes)
Step 4: Cooking Styles (optional, 2+ methods)
Step 5: Dietary Restrictions (multiple selection)
Step 6: Health Goals (up to 2 outcomes)
Step 7: FTP Account Credentials → Dashboard
```

### **Dashboard Navigation**
- **Cart Tab:** Live cart analysis with delivery date
- **Meals Tab:** Weekly meal calendar with drag-and-drop (Monday-Friday)
- **Settings Tab:** Update any preferences via modal editing

### **Important Business Rules**
- **Cart Lock Time:** Carts lock at 11:59 AM ET the day before delivery
- **Fallback Logic:** When cart is locked, system uses stored cart data with complete boxes
- **Protein Requirements:** Women: 30g minimum, Men: 35-40g minimum per meal

### **Settings System (Full CRUD)**
- **Household Size:** 1-7+ people grid selection
- **Meal Preferences:** Familiar vs adventurous dishes
- **Cooking Style:** Quick, comfort, international methods
- **Dietary Restrictions:** Allergies, lifestyle choices
- **Health Goals:** Quick dinners, family meals, etc.

---

## 📱 SMS FLOW (Secondary - Future Enhancement)

### **Message Routing (server.py:455-498)**
```python
if "hello" in user_message:
    reply = format_sms_with_help(
        "Hi there! I'm your Farm to People meal planning assistant.", 
        'greeting'
    )

elif "plan" in user_message:
    reply = format_sms_with_help(
        "📦 Analyzing your Farm to People cart...", 
        'analyzing'
    )
    background_tasks.add_task(run_full_meal_plan_flow, user_phone_number)

elif "new" in user_message:
    # User registration with secure login link + onboarding help

elif "login" in user_message or "email" in user_message:
    # Secure credential collection link + login help
```

### **SMS Help Text System (NEW - Aug 26, 2025)**
Every SMS now includes contextual help text to guide users:

**Example Output:**
```
📦 Analyzing your cart...
━━━━━━━━━
⏳ This takes 20-30 seconds...
```

**Available States:**
- `analyzing` - Progress indicator during processing  
- `plan_ready` - Action options after meal plan delivery
- `greeting` - Basic navigation for new users
- `error` - Recovery options when issues occur
- `default` - General help for unrecognized input

**Implementation:** `format_sms_with_help(message, state)` in server.py:111-178

### **Progress SMS Updates**
```python
# Background flow sends these messages:
1. "🔍 Looking up your account..."
2. "🔐 Found your account! Logging into Farm to People..."  
3. "📦 Analyzing your current cart and customizable boxes..."
4. "🤖 Generating personalized meal plans with your ingredients..."
5. [Final meal plan SMS]
```

---

## 📅 **MEAL CALENDAR SYSTEM (NEW - Aug 31, 2025)**

### **Revolutionary Feature: Drag & Drop Meal Planning**
Transform cart contents into interactive weekly meal calendar with smart ingredient allocation.

### **Key Innovations:**
- **Smart Ingredient Tracking** - System prevents over-allocation of ingredients
- **Drag & Drop Interface** - Move meals between days with real-time conflict detection  
- **Context-Aware Regeneration** - AI considers remaining ingredients when recreating meals
- **Cross-Device Sync** - Seamless planning across phone and desktop

### **Architecture:**
```
Cart Data → Ingredient Pool → Weekly Calendar → Meal Assignments
     ↓            ↓               ↓              ↓
   JSON        Database       React UI     Supabase Storage
```

### **Database Schema (4 New Tables):**
- `weekly_meal_plans` - Main meal plan containers
- `meal_assignments` - Individual meals per day (Mon-Fri)
- `ingredient_pools` - Track ingredient allocation/availability  
- `meal_plan_sessions` - Cross-device sync sessions

### **User Flow Example:**
1. **Generate Plan** - AI creates 5-day meal plan from cart
2. **Review Calendar** - See Monday-Friday with assigned meals
3. **Drag to Modify** - Move Tuesday's chicken to Thursday
4. **Auto-Validation** - System checks ingredient availability
5. **Smart Regeneration** - Click refresh on Tuesday for new meal
6. **Conflict Resolution** - Suggest alternatives if ingredients insufficient

### **Storage Architecture (Redis-Ready):**
```python
# Abstract storage layer for easy migration
storage = SupabaseMealStorage()  # Current
# storage = RedisMealStorage()   # Future (>100 users)

# Key operations:
await storage.create_meal_plan(user_phone, week_of, cart_data)
await storage.assign_meal(plan_id, "monday", meal_data, ingredients)
await storage.get_ingredient_pool(plan_id)  # Real-time availability
```

### **Status:** 
- ✅ **Backend Complete** - Database schema, storage layer, conflict detection
- 🚧 **API Endpoints** - In development (meal CRUD, regeneration)
- 📅 **Frontend** - Starting soon (drag & drop calendar component)

---

## 🛒 COMPREHENSIVE SCRAPER FUNCTIONALITY

### **Primary Scraper: comprehensive_scraper.py**

**Captures ALL Cart Types:**
1. **Individual Items** (eggs, avocados, bananas)
2. **Non-customizable Boxes** (Seasonal Fruit Medley)  
3. **Customizable Boxes** (Cook's Box - Paleo with alternatives)

**Current JSON Output Structure:**
```json
{
  "individual_items": [
    {
      "name": "Organic Hass Avocados",
      "quantity": 5,
      "unit": "1 piece", 
      "price": "$12.50",
      "type": "individual"
    }
  ],
  "non_customizable_boxes": [
    {
      "box_name": "Seasonal Fruit Medley",
      "selected_items": [...],
      "selected_count": 3,
      "customizable": false
    }
  ],
  "customizable_boxes": [
    {
      "box_name": "The Cook's Box - Paleo",
      "selected_items": [...],
      "available_alternatives": [...],
      "selected_count": 9,
      "alternatives_count": 10
    }
  ]
}
```

---

## 📊 CURRENT IMPLEMENTATION STATUS

### ✅ **COMPLETED FEATURES (as of 8/31)**
- **✅ Web App Foundation** - Complete 7-step onboarding with smart user detection
- **✅ Settings System** - Full CRUD operations for all user preferences
- **✅ Dashboard Integration** - Live cart data with meal suggestions and refresh functionality
- **✅ Cart Scraping** - Comprehensive capture including delivery date extraction
- **✅ User Management** - Phone-first flow with existing user skip logic
- **✅ Database Schema** - Supabase user/preference storage with encrypted credentials
- **✅ Live Cart → Dashboard** - Real FTP data integration with fallback to mock data
- **✅ Navigation System** - Clean tab structure (Cart/Meals/Settings) with proper routing
- **✅ GPT-5 Implementation** - Production-ready meal plan generation
- **✅ Deployment** - Live on Railway with environment variables configured
- **✅ Meal Calendar System** - Interactive weekly planning with drag & drop functionality
- **✅ Ingredient Pool Tracking** - Real-time allocation with visual progress bars
- **✅ Meal Variety Engine** - Different proteins/cooking methods each day
- **✅ Preference Integration** - User goals shape meal generation (high-protein, quick dinners)
- **✅ Cross-device Foundation** - Session management API for multi-device sync

### ✅ **COMPLETED THIS WEEK (8/31 - MEAL CALENDAR SPRINT)**
- **✅ Saturday:** Complete meal planning database schema with ingredient allocation
- **✅ Saturday:** Meal planning API with CRUD operations and conflict detection
- **✅ Saturday:** User preference integration in meal generation algorithms
- **✅ Saturday:** Meal variety system (different proteins/cooking methods per day)
- **✅ Saturday:** Interactive meal calendar interface with drag & drop
- **✅ Saturday:** Ingredient pool tracking with real-time progress visualization
- **✅ Saturday:** Mobile-responsive calendar design with touch-friendly interactions
- **✅ Saturday:** Complete documentation of meal calendar system

### ✅ **PREVIOUS WEEK (8/26-8/28)**
- **✅ Monday:** Settings page with 5 preference categories and modal editing
- **✅ Tuesday:** Dashboard navigation refactor (Home→Cart, Cart→Meals)
- **✅ Wednesday:** Live scraper integration with database credential lookup
- **✅ Wednesday:** Delivery date extraction from cart pages
- **✅ Wednesday:** Meal refresh functionality with 3x daily limit
- **✅ Thursday:** Onboarding flow refactor - phone number first with user detection
- **✅ Thursday:** Production deployment with full end-to-end testing

### 📝 **FUTURE FEATURES**
- **Confirmation Flow** - User approval before recipe generation
- **Cart Total Calculation** - Pricing transparency
- **Weekly Feedback Loop** - Recipe rating system
- **Seasonal Intelligence** - Produce availability awareness
- **Preference Evolution** - Learning from user behavior

---

## 🚨 CRITICAL GAPS & HANDOFF ISSUES

### **Gap 1: Preferences → Meal Planning**
**Issue**: Collected preferences not utilized in GPT prompts  
**Impact**: Missing personalization opportunity despite data collection  
**Solution**:
```python
# In server.py run_full_meal_plan_flow():
user_record = db.get_user_by_phone(phone_number)
preferences = user_record.get('preferences', {})

# Pass to meal_planner:
plan = meal_planner.run_main_planner(preferences)  # ADD THIS
```

### **Gap 2: Live Cart → Real Analysis**
**Issue**: Scraper works but test data still used  
**Impact**: Recommendations don't reflect actual purchased ingredients  
**Solution**: Ensure meal_planner uses actual scraped JSON data

### **Gap 3: Goals → Ranking Logic**
**Issue**: Goal weights defined but not implemented  
**Impact**: "Quick dinners" goal doesn't prioritize fast recipes  
**Solution**: Implement ranking adjustments based on goals

---

## 💻 KEY CODE COMPONENTS

### **Core Files (Reorganized 8/26)**
```
server/
├── server.py                 # FastAPI webhook & orchestration ✅
├── meal_planner.py          # GPT-5 integration ✅
├── onboarding.py            # Preference analysis engine ✅
├── supabase_client.py       # Database operations ✅
└── templates/               # HTML templates

generators/                  # NEW: PDF/HTML generation
├── pdf_minimal.py           # Penny-style PDF generator ✅
├── html_meal_plan_generator.py # HTML meal plans ✅
└── templates/
    └── meal_plan_minimal.html # BEST DESIGN: Clean, no emojis ✅

scrapers/
├── comprehensive_scraper.py  # PRIMARY: Full cart extraction ✅
└── auth_helper.py           # Authentication handling ✅

tests/                       # NEW: All test files moved here
docs/                        # Consolidated documentation
├── ARCHITECTURE.md          # System design
├── BUSINESS_FLOW.md         # User journey
└── DEVELOPMENT.md           # Setup & deployment
```

---

## 🔧 DEVELOPMENT COMMANDS

### **Essential Testing**
```bash
# ALWAYS activate venv first:
source venv/bin/activate

# Test primary scraper:
cd scrapers
python comprehensive_scraper.py

# Check latest output:
ls -lt ../farm_box_data/customize_results_*.json | head -1

# Verify JSON structure:
head -20 ../farm_box_data/customize_results_20250822_093323.json
```

### **Server Operations**
```bash
# Start server:
python server/server.py

# Check running processes:
ps aux | grep "python.*server.py"

# Kill server (use actual PID):
kill [PID]

# Test SMS flow:
curl -X POST http://localhost:8000/test-full-flow
```

---

## 🚨 CRITICAL ENVIRONMENT VARIABLES

```bash
# Required in .env file
EMAIL=your@email.com              # Farm to People login (or FTP_EMAIL)
PASSWORD=yourpassword             # Farm to People password (or FTP_PWD)
VONAGE_API_KEY=xxx               # SMS service
VONAGE_API_SECRET=xxx            
VONAGE_PHONE_NUMBER=18334391183  # System phone number
YOUR_PHONE_NUMBER=+1234567890    # Test recipient
OPENAI_API_KEY=xxx               # GPT-4 access
SUPABASE_URL=xxx                 # Database URL
SUPABASE_KEY=xxx                 # Database key
```

---

## 📈 KEY METRICS & TARGETS

### **Web App Performance**
- Onboarding Completion: >85% target (7-step flow)
- Existing User Recognition: >95% accuracy
- Cart Scraping Speed: <30 seconds with real credentials
- Dashboard Load Time: <3 seconds
- Settings Update Success: >99%

### **Technical Performance**
- Scraper Success Rate: >95% (✅ tested with real data)
- Database Operations: >99% uptime (Supabase)
- Railway Deployment: >99.5% availability
- AI Response Quality: GPT-5 production ready

### **Protein Requirements (NEW)**
- Women: 30g minimum per meal
- Men: 35-40g minimum per meal
- All meals must show protein content

---

## 🎯 NEXT SPRINT GOALS (Priority Order)

### **✅ Sprint 1: Web App Foundation (COMPLETED 8/28)**
1. ✅ Complete 7-step onboarding with user detection
2. ✅ Build settings system with full CRUD operations  
3. ✅ Connect live cart data to dashboard
4. ✅ Deploy to production on Railway

### **🚧 Sprint 2: Meal Planning Integration (Week of 9/2)**
1. Connect user preferences to GPT-5 meal generation
2. Generate recipe PDFs with full cooking instructions
3. Add cart total calculations with pricing transparency
4. Implement confirmation flow before recipe generation

### **📋 Sprint 3: User Experience Polish (Week of 9/9)**
1. Add meal calendar visualization for weekly planning
2. Build weekly feedback collection and rating system
3. Implement error recovery and retry mechanisms
4. Add analytics tracking for user behavior insights

### **🔮 Sprint 4: Advanced Features (Week of 9/16)**
1. SMS integration for notifications and updates
2. Seasonal intelligence for produce availability
3. Learning system that evolves with user preferences
4. Advanced personalization based on cooking history

---

## 🆘 TROUBLESHOOTING

### **Common Issues**
```bash
# Virtual environment not activated
command not found: python
# Fix: source venv/bin/activate

# Server not restarting
Changes not reflected
# Fix: ps aux | grep server.py && kill [PID]

# Scraper authentication fails
Zipcode modal appears
# Fix: Check EMAIL/PASSWORD in .env

# Cart data not updating
Using old test data
# Fix: Check meal_planner.py uses latest JSON

# Terminal shows no comprehensive output
Missing individual items or boxes
# Fix: venv not activated OR authentication failed
```

---

## 📞 SUPPORT & RESOURCES

- **GitHub Issues:** Report bugs at project repository
- **Documentation:** See `/docs` folder for detailed guides
- **Test Data:** Sample JSONs in `/farm_box_data`
- **Logs:** Check terminal output and `server.log`
- **Debug Protocol:** ALWAYS check DEBUGGING_PROTOCOL.md first

---

## 🚀 DEPLOYMENT CHECKLIST

- [ ] All tests passing
- [ ] Environment variables configured
- [ ] Database migrations complete
- [ ] Vonage webhook configured
- [ ] SSL certificates ready
- [ ] Monitoring enabled (Sentry/DataDog)
- [ ] Error tracking setup
- [ ] Documentation updated
- [ ] Conversation state management tested
- [ ] Rate limiting configured

---

**Last Updated:** August 24, 2025  
**Version:** 2.1.0  
**Status:** Development - Core complete, integration gaps identified  
**Next Sprint:** Week of August 26 - Core Integration Focus

*This guide provides the essential information for developing and maintaining the Farm to People AI Assistant. For detailed implementation specifics, refer to the documentation index above.*