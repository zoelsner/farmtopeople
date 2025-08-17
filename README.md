# 🍅 Farm to People AI Assistant

> **SMS-based meal planning system that scrapes your cart and generates personalized recipes**

## 🎯 **What It Does**

Text "plan" to get AI-generated meal plans based on your current Farm to People cart contents:

1. **📱 SMS Trigger** - Text "plan" to the system
2. **🔐 Auto-Login** - Securely logs into your FTP account  
3. **🛒 Cart Analysis** - Scrapes your cart + customizable box alternatives
4. **🤖 AI Planning** - OpenAI generates personalized meal plans
5. **📲 SMS Delivery** - Sends recipes back via text

## ✅ **Current Status: Production Ready**

- **✅ Multi-user support** via Supabase database
- **✅ Cloud deployed** on Railway.app  
- **✅ SMS integration** via Vonage
- **✅ Robust authentication** with fresh sessions
- **✅ Full cart scraping** including alternatives
- **✅ AI meal planning** via OpenAI GPT-4

## 🏗️ **Architecture**

```
SMS → Vonage → Railway Server → Supabase (credentials)
                    ↓
               Playwright Scraper → Farm to People
                    ↓
               OpenAI Meal Plans → SMS Response
```

## 🚀 **Quick Start**

### For Users:
1. **Get added to database** (contact admin)
2. **Text "plan"** to the system number
3. **Receive meal plan** via SMS

### For Developers:
```bash
# Clone and setup
git clone <repo>
cd farmtopeople
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Add your API keys and credentials

# Test locally
python scrapers/customize_scraper.py
python server/server.py
```

## 📁 **Key Files**

### Production Code:
- **`server/server.py`** - FastAPI server handling SMS webhooks
- **`scrapers/customize_scraper.py`** - Main production scraper
- **`meal_planner.py`** - OpenAI meal plan generation
- **`supabase_client.py`** - Database operations

### Documentation:
- **`CRITICAL_SCRAPING_LESSONS_LEARNED.md`** - ⚠️ READ BEFORE CHANGING CODE
- **`DEBUGGING_PROTOCOL.md`** - Mandatory debugging checklist
- **`ARCHITECTURE_OVERVIEW.md`** - Complete system architecture
- **`RAILWAY_DEPLOYMENT_GUIDE.md`** - Deployment instructions

## 🔧 **Environment Variables**

```bash
# Vonage SMS
VONAGE_API_KEY=your_key
VONAGE_API_SECRET=your_secret
VONAGE_PHONE_NUMBER=your_number

# OpenAI
OPENAI_API_KEY=sk-proj-...

# Supabase
SUPABASE_URL=https://...
SUPABASE_KEY=...

# Farm to People Credentials
EMAIL=your@email.com
PASSWORD=your_password
```

## 🧪 **Testing**

```bash
# Test scraper directly
cd scrapers
python customize_scraper.py

# Test server locally
python server/server.py

# Simulate SMS
curl -X POST localhost:8000/sms/incoming \
  -d "msisdn=4254955323&text=plan"
```

## 📊 **Features**

- **🔐 Secure Authentication** - Fresh browser sessions per request
- **🛒 Complete Cart Analysis** - Extracts selected items + alternatives
- **🤖 Smart Meal Planning** - AI-generated recipes using your ingredients
- **📱 SMS Interface** - Simple text commands
- **☁️ Cloud Ready** - Deployed on Railway.app
- **👥 Multi-User** - Secure credential management via Supabase

## ⚠️ **Important Notes**

1. **Always test working scripts first** - See `DEBUGGING_PROTOCOL.md`
2. **Server restart required** after code changes (Python module caching)
3. **Fresh browser sessions** prevent authentication issues
4. **Two-step login** - Email → LOG IN → Password → LOG IN

## 🚨 **SMS Opt-In Policy**

This service sends SMS messages only in response to user requests:
- **Opt-in**: Text "plan" or "new" to start
- **Opt-out**: Text "STOP" to stop messages
- **Help**: Text "HELP" for assistance
- **No marketing**: Only transactional meal planning messages
- **Privacy**: Data not shared with third parties

## 📞 **Support**

- **Issues**: Check `DEBUGGING_PROTOCOL.md` first
- **Lessons**: See `CRITICAL_SCRAPING_LESSONS_LEARNED.md`
- **Architecture**: Read `ARCHITECTURE_OVERVIEW.md`

---

**Status**: ✅ Production Ready | **Last Updated**: August 17, 2025
