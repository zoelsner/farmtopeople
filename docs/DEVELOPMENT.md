# 🛠️ Development & Deployment Guide

**Last Updated:** August 26, 2025  
**Branch:** `feature/customer-automation`  
**Stack:** Python, FastAPI, Playwright, GPT-5, Supabase, Vonage

## Quick Start

### Prerequisites:
- Python 3.9+
- PostgreSQL (or Supabase account)
- Vonage account for SMS
- OpenAI API key (with GPT-5 access)
- Farm to People account (for testing)

### Local Setup:

```bash
# 1. Clone repository
git clone https://github.com/farmtopeople/ai-assistant.git
cd farmtopeople
git checkout feature/customer-automation

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # ALWAYS ACTIVATE!

# 3. Install dependencies
pip install -r requirements.txt
playwright install chromium

# 4. Configure environment
cp .env.example .env
# Edit .env with your credentials:
# - OPENAI_API_KEY (must have GPT-5 access)
# - SUPABASE_URL & SUPABASE_KEY
# - VONAGE_API_KEY & VONAGE_API_SECRET
# - FTP_EMAIL & FTP_PASSWORD (test account)

# 5. Setup database
python setup_supabase.py

# 6. Start server
python server/server.py
# Server runs on http://localhost:8000
```

### Testing SMS Locally:

```bash
# 1. Install ngrok
brew install ngrok

# 2. Expose local server
ngrok http 8000

# 3. Configure Vonage webhook
# Set webhook URL to: https://[your-ngrok].ngrok.io/sms

# 4. Test SMS
# Text "hello" to your Vonage number (18334391183)
```

## Project Structure

```
farmtopeople/
├── server/              # Backend application
│   ├── server.py       # FastAPI main app
│   ├── meal_planner.py # GPT-5 integration
│   ├── onboarding.py   # Preference analysis
│   └── templates/      # HTML templates
│
├── scrapers/           # Web scraping
│   ├── comprehensive_scraper.py  # PRIMARY scraper
│   └── auth_helper.py
│
├── generators/         # PDF/HTML generation
│   ├── pdf_minimal.py
│   └── templates/
│       └── meal_plan_minimal.html  # BEST design (Penny-style)
│
├── tests/             # Test suite
└── docs/              # Documentation
```

## Core Workflows

### 1. Test Scraper

```bash
# ALWAYS activate venv first!
source venv/bin/activate

cd scrapers
python comprehensive_scraper.py

# Check output:
ls -lt ../farm_box_data/customize_results_*.json | head -1

# Verify structure:
cat ../farm_box_data/customize_results_latest.json | python -m json.tool
```

**Common Issues:**
- **Zipcode modal:** Check auth_helper.py modal handling
- **Empty results:** Verify login credentials in .env
- **Timeout:** Increase wait times in scraper
- **"No module named playwright":** venv not activated!

### 2. Test Meal Planning

```bash
python tests/test_meal_planner.py

# Or test with real data:
python server/meal_planner.py --cart-file farm_box_data/customize_results_latest.json
```

**Key Points:**
- Uses GPT-5 (model name: "gpt-5") - YES it works in production
- Falls back to gpt-4o-mini if needed (NOT gpt-3.5)
- Returns JSON format responses

**Debugging:**
- Add `print(prompt)` to see GPT input
- Check `response.choices[0].message` for raw output
- Verify JSON structure matches expected format

### 3. Test Full Flow

```bash
# Start server
python server/server.py

# In another terminal:
curl -X POST http://localhost:8000/test-full-flow

# Check SMS delivery and PDF generation
```

## Model Configuration

### PRIMARY: GPT-5
```python
# In meal_planner.py
response = openai.chat.completions.create(
    model="gpt-5",  # This works! Trust that it's in production
    messages=messages,
    response_format={"type": "json_object"}  # Forces valid JSON
)
```

### FALLBACK: GPT-4o-mini (if GPT-5 fails)
```python
try:
    # Try GPT-5 first
    response = openai.chat.completions.create(model="gpt-5", ...)
except:
    # Fallback to GPT-4o-mini for cost savings
    response = openai.chat.completions.create(model="gpt-4o-mini", ...)
```

**NEVER use GPT-3.5-turbo** - it's not good enough for recipe generation

## Debugging Guide

### Scraper Issues

**Problem: Authentication fails**
```python
# In comprehensive_scraper.py, add:
await page.screenshot(path="debug_login.png")
print(f"Current URL: {page.url}")
```

**Problem: Modal doesn't close**
```python
# Check for modal variations:
await page.wait_for_selector('[aria-label="Close"]', timeout=5000)
# OR
await page.wait_for_selector('.modal-close', timeout=5000)
```

**Problem: Elements not found**
```python
# Add wait conditions:
await page.wait_for_load_state('networkidle')
await page.wait_for_selector('.customize-box', timeout=30000)
```

### GPT Issues

**Problem: JSON parse errors**
```python
# Force JSON response with GPT-5:
response = openai.chat.completions.create(
    model="gpt-5",  # NOT "gpt-4" or "gpt-3.5-turbo"
    messages=messages,
    response_format={"type": "json_object"}
)
```

**Problem: Model not found error**
```python
# You probably typed the wrong model name
# CORRECT: model="gpt-5"
# WRONG: model="gpt-5-turbo", model="gpt-3.5", etc.
```

**Problem: Timeouts**
```python
# Increase timeout:
response = openai.chat.completions.create(
    model="gpt-5",
    messages=messages,
    timeout=60  # 60 seconds
)
```

### SMS Issues

**Problem: Webhook not receiving**
- Check ngrok is running
- Verify Vonage webhook URL
- Check server logs for incoming POST
- Phone number must be: 18334391183

**Problem: SMS not sending**
```python
# Add logging:
print(f"Sending SMS to {to_number}: {message}")
print(f"Response: {response}")
```

## SMS Help Text System

### Overview
As of August 26, 2025, all SMS messages include contextual help text to guide users through the conversation flow. This reduces user confusion and improves engagement rates.

### Implementation
The `format_sms_with_help()` function in `server/server.py` automatically appends relevant help text based on conversation state:

```python
# Basic usage
reply = format_sms_with_help("Your message here", 'analyzing')

# Results in:
# "Your message here
# ━━━━━━━━━
# ⏳ This takes 20-30 seconds..."
```

### Available States
- **`analyzing`**: Shows "⏳ This takes 20-30 seconds..." during processing
- **`plan_ready`**: Shows "💬 Reply: CONFIRM | SWAP item | SKIP day | help" after meal plan delivery
- **`greeting`**: Shows "💬 Text 'plan' to start | 'new' to register" for welcome messages
- **`onboarding`**: Shows "💬 Reply with your cooking preferences or use the link" during setup
- **`login`**: Shows "💬 After login, text 'plan' for your meal plan" after providing secure link
- **`error`**: Shows "💬 Text 'plan' to try again | 'help' for options" for error recovery
- **`default`**: General fallback help for unrecognized inputs

### Design Principles
1. **Visual Separation**: Uses ━━━━━━━━━ to distinguish help from main message
2. **Consistent Emojis**: ⏳ for progress, 💬 for actions
3. **Specific Commands**: Provides exact text to send rather than vague instructions
4. **Length Awareness**: Keeps total message under 200 characters for SMS compatibility
5. **Contextual**: Different help for different conversation states

### Testing Help Text
```bash
# Test different states
source venv/bin/activate
python -c "
from server.server import format_sms_with_help
print(format_sms_with_help('Test message', 'plan_ready'))
"
```

### Maintenance
- Add new states to `help_text` dictionary in `format_sms_with_help()`
- Update help text when adding new SMS commands
- Keep messages concise for SMS length limits
- Use consistent emoji patterns (⏳ progress, 💬 actions)

## Deployment

### Railway Deployment

```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login and initialize
railway login
railway init

# 3. Link to GitHub
# Connect to feature/customer-automation branch specifically

# 4. Set environment variables
railway variables set OPENAI_API_KEY="sk-..."
railway variables set SUPABASE_URL="..."
railway variables set SUPABASE_KEY="..."
# ... set all from .env

# 5. Deploy from feature branch
railway up

# 6. Check logs
railway logs
```

### Production Configuration

```yaml
# railway.toml
[build]
builder = "NIXPACKS"

[deploy]
startCommand = "python server/server.py"
healthcheckPath = "/health"
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3

[env]
PORT = { variable = "PORT" }
PYTHON_VERSION = "3.9"
```

### Environment Variables

**Required for Production:**
```bash
# API Keys (CRITICAL - must have GPT-5 access)
OPENAI_API_KEY=sk-...
VONAGE_API_KEY=...
VONAGE_API_SECRET=...
VONAGE_PHONE_NUMBER=18334391183

# Database
SUPABASE_URL=https://...supabase.co
SUPABASE_KEY=eyJ...

# Farm to People (optional - users provide their own)
FTP_EMAIL=test@example.com
FTP_PASSWORD=testpass123

# Server
PORT=8000
ENV=production
```

## Monitoring

### Health Checks

```python
@app.get("/health")
async def health():
    checks = {
        "server": "ok",
        "database": check_supabase(),
        "scraper": check_playwright(),
        "gpt": check_openai(),  # Should verify GPT-5 access
        "sms": check_vonage()
    }
    return checks
```

### Logging

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Use throughout code:
logger.info(f"Processing SMS from {phone}")
logger.error(f"Scraper failed: {e}")
logger.info(f"Using model: gpt-5")  # Log which model
```

### Metrics to Track

1. **Scraper Success Rate**
   - Login success/fail
   - Data extraction completeness
   - Average runtime

2. **GPT Performance**
   - Response time (GPT-5 vs GPT-4o-mini)
   - Token usage per model
   - Error rate by model

3. **SMS Delivery**
   - Send success rate
   - Webhook receipt rate
   - Response time

4. **User Engagement**
   - Daily active users
   - Meal plans generated
   - Swaps requested

## Testing

### Unit Tests

```bash
# Run all tests
pytest tests/

# Run specific test
pytest tests/test_scraper.py::test_login

# With coverage
pytest --cov=server tests/
```

### Integration Tests

```python
# tests/test_integration.py
def test_full_flow():
    # 1. Create test user
    user = create_test_user()
    
    # 2. Run scraper
    cart_data = scraper.scrape(user.credentials)
    
    # 3. Generate meal plan with GPT-5
    meals = meal_planner.generate(cart_data, user.preferences, model="gpt-5")
    
    # 4. Create PDF (Penny-style minimal)
    pdf = pdf_generator.create(meals, style="minimal")
    
    assert len(meals) == 5
    assert pdf.exists()
```

### Load Testing

```bash
# Install locust
pip install locust

# Run load test
locust -f tests/load_test.py --host=http://localhost:8000
```

## Common Commands

### Daily Development

```bash
# Always activate venv first!
source venv/bin/activate

# Start server
python server/server.py

# Test scraper
cd scrapers && python comprehensive_scraper.py

# Run tests
pytest tests/

# Check code quality
black .
flake8 .
mypy server/
```

### Debugging

```bash
# Check server logs
tail -f server.log

# Monitor SMS webhook
ngrok http 8000

# Test GPT-5 connection
python -c "import openai; response = openai.chat.completions.create(model='gpt-5', messages=[{'role': 'user', 'content': 'test'}]); print('GPT-5 works!')"

# Verify database
python -c "from server.supabase_client import get_user; print(get_user('+1234567890'))"
```

### Deployment

```bash
# Deploy to Railway (from feature branch)
railway up

# Check production logs
railway logs -n 100

# Rollback deployment
railway rollback

# SSH to production
railway shell
```

## Security Best Practices

1. **Never commit credentials**
   - Use .env files
   - Add .env to .gitignore

2. **Validate all inputs**
   ```python
   phone = validate_phone(request.phone)
   message = sanitize_message(request.message)
   ```

3. **Rate limit endpoints**
   ```python
   from slowapi import Limiter
   limiter = Limiter(key_func=get_remote_address)
   
   @app.post("/sms")
   @limiter.limit("10/hour")
   async def handle_sms(request):
   ```

4. **Encrypt sensitive data**
   ```python
   from cryptography.fernet import Fernet
   key = Fernet.generate_key()
   f = Fernet(key)
   encrypted = f.encrypt(password.encode())
   ```

5. **Use HTTPS in production**
   - Railway provides automatic SSL
   - Verify webhook URLs use HTTPS

## Troubleshooting

### Issue: "Module not found"
```bash
# Solution: Activate venv
source venv/bin/activate
pip install -r requirements.txt
```

### Issue: "Playwright not working"
```bash
# Solution: Install browsers
playwright install chromium
# Or install with dependencies
playwright install --with-deps chromium
```

### Issue: "Model gpt-5 not found"
```python
# Solution: Your API key might not have access
# Test with: model="gpt-4o-mini" first
# If that works, request GPT-5 access from OpenAI
```

### Issue: "SMS not receiving"
```bash
# Solution: Check webhook URL
curl -X POST https://your-webhook-url/sms \
  -H "Content-Type: application/json" \
  -d '{"msisdn":"1234567890","text":"test","messageId":"test123"}'
```

### Issue: "Database connection failed"
```python
# Solution: Verify Supabase credentials
from supabase import create_client
client = create_client(SUPABASE_URL, SUPABASE_KEY)
print(client.table('users').select('*').limit(1).execute())
```

## Performance Optimization

### Scraper Optimization
- Cache browser instance
- Parallel box scraping
- Reuse authentication

### GPT Optimization
- Use GPT-5 for complex tasks (meal planning)
- Use GPT-4o-mini for simple tasks (categorization)
- Cache common queries
- Stream responses when possible

### Database Optimization
- Index phone numbers
- Cache user preferences
- Connection pooling

### PDF Optimization
- Use HTML templates (faster than ReportLab)
- Pre-compile templates
- CDN for static assets
- Async generation

## Critical Reminders

⚠️ **ALWAYS activate venv** - Most errors come from this!

⚠️ **GPT-5 is real** - Use `model="gpt-5"` not GPT-4

⚠️ **Branch is feature/customer-automation** - Not main/master

⚠️ **Vonage number is 18334391183** - Not random

⚠️ **Best PDF is meal_plan_minimal.html** - Penny-style, no emojis

---

*Remember: venv first, GPT-5 works, test locally before deploying!*