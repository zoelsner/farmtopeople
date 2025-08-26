# Farm to People AI Assistant - Architecture Overview

## 🎯 System Architecture - Production Ready

### Overview
The Farm to People AI Assistant is a multi-user SMS-based meal planning system that:
1. Receives SMS commands via Vonage
2. Authenticates and scrapes user's Farm to People cart
3. Generates personalized meal plans using OpenAI
4. Delivers recipes via SMS

## 🔄 Complete Working Flow

```
User SMS "plan" → Vonage Webhook → FastAPI Server
                                         ↓
                                   Supabase Lookup
                                   (Get credentials)
                                         ↓
                                   Playwright Scraper
                                   (Fresh browser session)
                                         ↓
                                   Login to Farm to People
                                   (Two-step process)
                                         ↓
                                   Extract Cart Contents
                                   (Boxes + Alternatives)
                                         ↓
                                   OpenAI Meal Planning
                                   (Generate recipes)
                                         ↓
                                   Vonage SMS Response
                                   (Deliver meal plan)
```

## 🏗️ Core Components

### 1. **Server Layer** (`server/server.py`)
- FastAPI application handling webhooks
- Routes: `/webhook/inbound-sms`, `/login`
- Background task processing for scraping
- Dynamic credential management

### 2. **Authentication System**
- **Multi-User Support**: Fresh browser session per request
- **Credential Sources**: 
  - Supabase database (production)
  - Environment variables (fallback)
- **Login Flow**: Email → LOG IN → Password → LOG IN
- **Session Management**: No persistent browser data

### 3. **Scraping Engine** (`scrapers/customize_scraper.py`)
- **Primary Scraper**: Handles all cart types
- **Extracts**:
  - Customizable boxes with contents
  - Available alternatives for swaps
  - Individual items with quantities
- **Output**: JSON with complete cart structure

### 4. **AI Meal Planner** (`meal_planner.py`)
- OpenAI GPT-4 integration
- Generates 3 personalized recipes
- Validates ingredients against cart
- Handles repair for missing items

### 5. **Database Layer** (Supabase)
- User credentials storage
- Phone number → FTP credentials mapping
- Scalable PostgreSQL backend

## 🔐 Security & Authentication

### Environment Variables
```bash
# Vonage SMS
VONAGE_API_KEY=xxx
VONAGE_API_SECRET=xxx
VONAGE_PHONE_NUMBER=xxx

# OpenAI
OPENAI_API_KEY=xxx

# Supabase
SUPABASE_URL=xxx
SUPABASE_KEY=xxx

# Farm to People (fallback)
EMAIL=xxx  # or FTP_EMAIL
PASSWORD=xxx  # or FTP_PWD
```

### Authentication Flow
1. **Check Multiple Formats**: System tries various phone formats
2. **Supabase Lookup**: Get user's FTP credentials
3. **Dynamic Environment**: Set EMAIL/PASSWORD for scraper
4. **Fresh Session**: New browser context per user
5. **Smart Detection**: Multiple checks for login state

## 📊 Data Flow

### Input (SMS)
```
From: +14254955323
Text: "plan"
```

### Supabase Query
```sql
SELECT * FROM users 
WHERE phone IN ('+14254955323', '14254955323', '4254955323')
```

### Scraper Output
```json
{
  "box_name": "Seasonal Produce Box - Small",
  "selected_items": [...],
  "available_alternatives": [...],
  "total_items": 14
}
```

### SMS Response
```
🍽️ Your Farm to People meal plan is ready!

- Grilled Tuna with Roasted Vegetables
- Pork and Vegetable Stir-Fry  
- Fresh Peach and Tomato Salad

Enjoy your meals!
```

## 🚀 Deployment Checklist

### Prerequisites
- [ ] Python 3.8+ with virtual environment
- [ ] All dependencies from `requirements.txt`
- [ ] Vonage account with SMS number
- [ ] OpenAI API access
- [ ] Supabase project
- [ ] Public URL (ngrok for development)

### Setup Steps
1. Clone repository
2. Create virtual environment
3. Install dependencies: `pip install -r requirements.txt`
4. Configure `.env` file
5. Set Vonage webhook to `https://your-domain/webhook/inbound-sms`
6. Run server: `python server/server.py`

### Critical Reminders
- **Always restart server after code changes**
- **Use fresh browser sessions for multi-user**
- **Check both EMAIL/PASSWORD and FTP_EMAIL/FTP_PWD**
- **Monitor for zipcode modal (indicates auth failure)**

## 📈 Scaling Considerations

### Current Capacity
- Handles concurrent users with separate browser sessions
- Each request gets fresh authentication
- No session conflicts between users

### Future Enhancements
1. **Queue System**: Add Redis for job queuing
2. **Worker Pool**: Multiple scraper instances
3. **Caching**: Store recent scrapes
4. **Scheduling**: Automated Thursday scraping
5. **PDF Generation**: Visual meal plans

## 🔍 Debugging Quick Reference

### Common Issues
1. **"Clicking zipcode modal"** → Not authenticated
2. **"No module named auth_helper"** → Import path issue
3. **"No credentials found"** → Check .env loading
4. **"Old behavior persists"** → Restart server

### Debug Commands
```bash
# Check server process
ps aux | grep "python.*server.py"

# Test scraper directly
EMAIL=test@example.com PASSWORD=xxx python scrapers/customize_scraper.py

# Check Supabase connection
python -c "from server.supabase_client import get_user_by_phone; print(get_user_by_phone('+14254955323'))"
```

---

**Last Updated**: August 17, 2025
**Status**: ✅ PRODUCTION READY
