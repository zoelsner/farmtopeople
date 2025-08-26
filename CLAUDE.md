# 🤖 CLAUDE.md - Farm to People AI Assistant Development Guide

## 🎯 PROJECT OVERVIEW

**Farm to People AI Assistant** transforms weekly produce boxes into personalized meal plans through intelligent SMS conversations. The system learns user preferences, analyzes cart contents, and delivers actionable cooking guidance.

**Current Status:** Development Phase - Core functionality complete, preparing for production deployment  
**Last Updated:** August 26, 2025  
**Version:** 2.2.0  
**Branch:** `feature/customer-automation`  
**Primary Contact:** SMS `18334391183` (Vonage)

---

## 🚀 QUICK START

### **Test the System**
```bash
# 1. Activate virtual environment (REQUIRED)
source venv/bin/activate

# 2. Start the server
python server/server.py

# 3. Test onboarding flow
open http://localhost:8000/onboard

# 4. Test cart scraping
cd scrapers && python comprehensive_scraper.py

# 5. Simulate SMS flow
curl -X POST http://localhost:8000/test-full-flow
```

### **Critical Development Rules**
- ✅ ALWAYS activate venv before running Python code
- ✅ Use GPT-5 (model="gpt-5") - it works in production!
- ✅ Test comprehensive_scraper.py before making changes
- ✅ Restart server after code modifications
- ✅ Best PDF design: `generators/templates/meal_plan_minimal.html` (Penny-style)
- ✅ NEVER use GPT-3.5 - use GPT-5 or gpt-4o-mini only

---

## 📚 DOCUMENTATION INDEX

### **Business & Product Docs**
- [`docs/complete_business_flow.md`](docs/complete_business_flow.md) - End-to-end customer journey with confirmation flow
- [`docs/updated_business_flow.md`](docs/updated_business_flow.md) - Latest requirements (high-protein, meal calendar)
- [`docs/system_gap_analysis.md`](docs/system_gap_analysis.md) - Current gaps and improvement roadmap
- [`docs/ONBOARDING_SYSTEM.md`](docs/ONBOARDING_SYSTEM.md) - Preference collection implementation

### **Technical Documentation**
- [`docs/refactoring_opportunities.md`](docs/refactoring_opportunities.md) - Architecture improvements & conversation state management
- [`docs/conversational_ai_architecture.md`](docs/conversational_ai_architecture.md) - AI system design patterns
- [`DEBUGGING_PROTOCOL.md`](DEBUGGING_PROTOCOL.md) - Scraper troubleshooting guide
- [`CRITICAL_SCRAPING_LESSONS_LEARNED.md`](CRITICAL_SCRAPING_LESSONS_LEARNED.md) - Historical failures & solutions

---

## 🏗️ SYSTEM ARCHITECTURE

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   ONBOARDING │────▶│   SMS FLOW   │────▶│   DELIVERY   │
│   (6 steps)  │     │  (Vonage)    │     │   (PDF/Web)  │
└──────────────┘     └──────────────┘     └──────────────┘
        │                    │                     │
        ▼                    ▼                     ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   SUPABASE   │◀────│   SCRAPER    │────▶│   GPT-4/5    │
│ (Preferences)│     │ (Playwright) │     │   (Meals)    │
└──────────────┘     └──────────────┘     └──────────────┘
```

---

## 📱 CURRENT SMS FLOW

### **Message Routing (server.py:215-239)**
```python
if "hello" in user_message:
    reply = "Hi there! I'm your Farm to People meal planning assistant."

elif "plan" in user_message:
    reply = "We are preparing your personalized meal plan now..."
    background_tasks.add_task(run_full_meal_plan_flow, user_phone_number)

elif "new" in user_message:
    # User registration with secure login link

elif "login" in user_message or "email" in user_message:
    # Secure credential collection link
```

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

### ✅ **COMPLETED FEATURES (as of 8/26)**
- **Onboarding System** - 6-step preference collection with FTP integration
- **Cart Scraping** - Comprehensive capture of all cart types
- **SMS Integration** - Vonage webhook with progress updates
- **Preference Analysis** - 20-30 signal extraction system
- **Database Schema** - Supabase user/preference storage
- **Live Cart → Meal Planner** - Direct data connection (no files) ✅
- **Preference → GPT Integration** - Preferences shape meal generation ✅
- **GPT-5 Implementation** - Using production GPT-5 (not GPT-4) ✅
- **PDF Generation** - Penny-style minimal design (HTML→PDF) ✅
- **Ingredient Storage Guide** - Proper storage instructions

### 🚧 **THIS WEEK (8/26-8/30)**
- **Tuesday PM:** Add help text to SMS responses
- **Wednesday:** Redis conversation state management
- **Thursday AM:** Instant acknowledgments
- **Thursday PM:** Modification handlers (swap/skip/remove)
- **Friday:** Test with real data & deploy to production

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

### **User Experience**
- Onboarding Completion: >85% target
- Cart Analysis Speed: <30 seconds
- Confirmation Rate: >80% target
- Recipe Execution: >70% cook 2+ meals/week

### **Technical Performance**
- Scraper Success Rate: >95%
- SMS Delivery Rate: >99%
- AI Response Quality: >8/10 satisfaction
- System Uptime: >99.5%

### **Protein Requirements (NEW)**
- Women: 30g minimum per meal
- Men: 35-40g minimum per meal
- All meals must show protein content

---

## 🎯 NEXT SPRINT GOALS (Priority Order)

### **Sprint 1: Core Integration (Week 1)**
1. Connect live cart data to meal planner
2. Integrate user preferences into GPT prompts
3. Implement conversation state management
4. Add confirmation flow with modifications

### **Sprint 2: User Experience (Week 2)**
1. Generate recipe PDFs with full instructions
2. Add cart total calculations
3. Implement meal calendar visualization
4. Build weekly feedback collection

### **Sprint 3: Production Ready (Week 3)**
1. Deploy to Railway with monitoring
2. Add error recovery and retries
3. Implement caching strategy
4. Set up analytics tracking

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