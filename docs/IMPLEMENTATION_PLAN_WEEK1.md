# 📋 Farm to People - Week 1 Implementation Plan
*Ship Date: End of This Week*  
*Strategy: Connect existing pieces, add visibility, maintain stability*

## 🎯 GOAL: Ship Working MVP with Real Value
**Core Achievement**: Connect the "Ferrari engine" (comprehensive scraper) to deliver personalized meal plans using actual cart data and user preferences.

### **Accelerated Approach Benefits**
- **Monday**: Both core connections done in one day
- **Tuesday**: PDFs ready by end of day
- **Wednesday**: Redis ensures no context loss during deployment
- **Thursday**: Full modification flow working
- **Friday**: Ship with confidence

---

## 📊 CURRENT STATE vs. END OF WEEK STATE

### Current State ✓
- ✅ Comprehensive scraper capturing all cart data
- ✅ User preference collection (20-30 signals)
- ✅ SMS integration working
- ✅ Database storing preferences
- ⚠️ Using test data instead of real cart
- ⚠️ Preferences collected but not used
- ⚠️ No conversation state tracking
- ⚠️ No user guidance in SMS

### Target State (End of Week)
- ✅ Real cart data → Personalized meal plans
- ✅ User preferences → GPT prompts
- ✅ Basic state tracking (in-memory)
- ✅ Help text in every SMS
- ✅ Instant acknowledgments
- ✅ PDF recipe generation
- ✅ Modification flow (swap/skip/remove)

---

## 🗓️ ACCELERATED TIMELINE (You're right - we can move faster!)

### **MONDAY: Core Connections**
**Morning (2 hrs):** Connect scraper → meal planner  
**Afternoon (2 hrs):** Add preferences → GPT prompts

#### Task 1: Connect Scraper to Meal Planner (AM)
```python
# In server/server.py, update run_full_meal_plan_flow():

async def run_full_meal_plan_flow(phone_number: str, credentials: Dict = None):
    try:
        # CHANGE 1: Use real scraper data
        from scrapers.comprehensive_scraper import scrape_farm_to_people
        
        if not credentials:
            user = supabase_client.get_user_by_phone(phone_number)
            credentials = {
                'email': user.get('ftp_email'),
                'password': user.get('ftp_password')  # Encrypted
            }
        
        # Get REAL cart data
        cart_data = await scrape_farm_to_people(credentials)
        
        # CHANGE 2: Get user preferences
        preferences = user.get('preferences', {})
        
        # CHANGE 3: Pass both to meal planner
        from meal_planner import run_main_planner
        meal_plan = run_main_planner(
            cart_data=cart_data,
            user_preferences=preferences
        )
        
        return meal_plan
        
    except Exception as e:
        logger.error(f"Meal plan flow failed: {e}")
        return None
```

#### Task 2: Update Meal Planner to Accept Real Data (1 hr)
```python
# In server/meal_planner.py:

def run_main_planner(cart_data: Dict, user_preferences: Dict):
    # Format cart data for GPT
    cart_summary = format_cart_for_analysis(cart_data)
    
    # Extract preference signals
    dietary_restrictions = user_preferences.get('dietary_restrictions', [])
    preferred_proteins = user_preferences.get('preferred_proteins', [])
    cooking_methods = user_preferences.get('cooking_methods', [])
    goals = user_preferences.get('goals', [])
    
    # Build enhanced prompt
    prompt = build_personalized_prompt(
        cart_summary,
        dietary_restrictions,
        preferred_proteins,
        cooking_methods,
        goals
    )
    
    # Generate meal plan
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response.choices[0].message.content
```

#### Task 3: Test Connection (1 hr)
- Run comprehensive_scraper.py manually
- Feed output to meal_planner
- Verify personalized output

---

### **TUESDAY: Intelligence + PDFs**
**Morning (2 hrs):** PDF recipe generation  
**Afternoon (1 hr):** Help text everywhere

#### Task 1: Enhanced GPT Prompts with Preferences (2 hrs)
```python
def build_personalized_prompt(cart_data, prefs):
    prompt = f"""
You are a meal planning assistant for Farm to People customers.

USER PREFERENCES:
- Household size: {prefs.get('household_size', 2)}
- Meal timing: {', '.join(prefs.get('meal_timing', ['dinner']))}
- Dietary restrictions: {', '.join(prefs.get('dietary_restrictions', ['none']))}
- Preferred proteins: {', '.join(prefs.get('preferred_proteins', []))}
- Cooking style: {', '.join(prefs.get('cooking_methods', []))}
- Goals: {', '.join(prefs.get('goals', []))}

PROTEIN REQUIREMENTS:
- Women: 30g minimum per meal
- Men: 35-40g minimum per meal

CURRENT CART:
{cart_data}

TASK:
1. Analyze what meals can be made with current items
2. Identify protein gaps for complete meals
3. Suggest specific additions to meet protein goals
4. Create 5-7 meals that match preferences
5. Include protein content for each meal

Format response for SMS delivery (concise but informative).
"""
    return prompt
```

#### Task 2: Add PDF Recipe Generation (2 hrs)
```python
# In server/recipe_generator.py (new file):

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

def generate_recipe_pdf(meal_plan: Dict, user_name: str):
    filename = f"recipes_{user_name}_{datetime.now().strftime('%Y%m%d')}.pdf"
    doc = SimpleDocTemplate(filename, pagesize=letter)
    
    # Build PDF content
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    title = Paragraph(f"Your Farm to People Meal Plan", styles['Title'])
    elements.append(title)
    
    # Add each recipe
    for meal in meal_plan['meals']:
        elements.append(Paragraph(meal['name'], styles['Heading2']))
        elements.append(Paragraph(f"Protein: {meal['protein']}g", styles['Normal']))
        elements.append(Paragraph(f"Time: {meal['cook_time']} min", styles['Normal']))
        
        # Ingredients
        elements.append(Paragraph("Ingredients:", styles['Heading3']))
        for ing in meal['ingredients']:
            elements.append(Paragraph(f"• {ing}", styles['Normal']))
        
        # Instructions
        elements.append(Paragraph("Instructions:", styles['Heading3']))
        for i, step in enumerate(meal['instructions'], 1):
            elements.append(Paragraph(f"{i}. {step}", styles['Normal']))
    
    doc.build(elements)
    return filename
```

---

### **WEDNESDAY: Redis State Management** 
**Time: 4 hours**  
**Why Redis:** You won't lose context when you push updates or restart the server!

See full implementation: [`docs/REDIS_STATE_MANAGEMENT.md`](./REDIS_STATE_MANAGEMENT.md)

#### Task 1: Add Help Text to All SMS (1 hr)
```python
# In server/server.py:

def format_sms_with_help(message: str, state: str = None):
    """Add contextual help to every SMS"""
    
    help_text = {
        'analyzing': "━━━━━━━━━\n⏳ This takes 20-30 seconds...",
        'analysis_sent': "━━━━━━━━━\n💬 Reply: yes | swap X for Y | skip Day | help",
        'confirmed': "━━━━━━━━━\n✅ Recipes coming! Reply 'recipes now' for instant delivery",
        'default': "━━━━━━━━━\n💬 Text 'plan' to start | 'help' for options"
    }
    
    return f"{message}\n{help_text.get(state, help_text['default'])}"
```

#### Task 2: Implement Basic State Tracking (2 hrs)
```python
# In server/server.py:

# Simple in-memory state (no Redis needed yet)
conversation_states = {}

class ConversationState:
    def __init__(self, phone):
        self.phone = phone
        self.status = 'idle'
        self.last_analysis = None
        self.modifications = []
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
    
    def update(self, new_status, data=None):
        self.status = new_status
        self.last_activity = datetime.now()
        if data:
            self.last_analysis = data
    
    def add_modification(self, mod_type, details):
        self.modifications.append({
            'type': mod_type,
            'details': details,
            'timestamp': datetime.now()
        })
    
    def is_expired(self):
        return (datetime.now() - self.last_activity).seconds > 7200  # 2 hours

async def handle_sms_webhook(request: Request):
    data = await request.form()
    phone = data.get('From')
    message = data.get('Body', '').lower()
    
    # Get or create state
    if phone not in conversation_states or conversation_states[phone].is_expired():
        conversation_states[phone] = ConversationState(phone)
    
    state = conversation_states[phone]
    
    # Route based on message AND state
    if 'plan' in message:
        state.update('analyzing')
        response = "📦 Analyzing your Farm to People cart..."
        # Trigger background analysis
        background_tasks.add_task(run_full_meal_plan_flow, phone)
        
    elif state.status == 'analysis_sent':
        if 'yes' in message or 'confirm' in message:
            state.update('confirmed')
            response = "✅ Perfect! Generating your recipes..."
            # Generate PDF
            background_tasks.add_task(generate_and_send_recipes, phone, state.last_analysis)
            
        elif 'swap' in message:
            # Parse swap request
            swap_details = parse_swap_request(message)
            state.add_modification('swap', swap_details)
            response = f"🔄 Swapping {swap_details['old']} for {swap_details['new']}..."
            # Regenerate analysis
            background_tasks.add_task(regenerate_analysis, phone, state)
            
        elif 'skip' in message:
            # Parse skip days
            skip_days = parse_skip_days(message)
            state.add_modification('skip', skip_days)
            response = f"📅 Removing {', '.join(skip_days)} from meal plan..."
            # Regenerate analysis
            background_tasks.add_task(regenerate_analysis, phone, state)
    
    else:
        response = "👋 Text 'plan' to get your personalized meal plan!"
    
    # Add help text
    response = format_sms_with_help(response, state.status)
    
    return create_vonage_response(response)
```

---

### **THURSDAY: Complete the Flow**
**Morning (2 hrs):** Instant acknowledgments + error handling  
**Afternoon (2 hrs):** Modification handlers (swap/skip/remove)

#### Task 1: Add Instant Acknowledgments (AM)
```python
async def send_instant_ack(phone: str, message_type: str):
    """Send immediate feedback while processing"""
    
    acks = {
        'plan': "👀 Got it! Analyzing your cart...",
        'confirm': "✅ Processing your confirmation...",
        'swap': "🔄 Making that swap...",
        'skip': "📅 Updating your calendar...",
        'help': "📚 Here's what I can do..."
    }
    
    vonage_client.send_message({
        'from': VONAGE_PHONE,
        'to': phone,
        'text': acks.get(message_type, "👍 Working on that...")
    })
```

#### Task 2: Full Flow Testing (3 hrs)
1. Test with real FTP account
2. Verify scraper → meal planner connection
3. Test all modification commands
4. Verify PDF generation
5. Test state persistence across messages

#### Task 3: Error Handling (1 hr)
```python
def safe_meal_plan_flow(phone):
    try:
        return run_full_meal_plan_flow(phone)
    except ScraperError:
        return "⚠️ Having trouble accessing your cart. Please try again in a moment."
    except OpenAIError:
        return "⚠️ Our meal planning service is busy. Please try again shortly."
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return "⚠️ Something went wrong. Reply 'help' for assistance."
```

---

### **FRIDAY: Test & Deploy**
**Morning (2 hrs):** Full integration testing with real accounts  
**Afternoon (2 hrs):** Deploy to production + monitor

1. Test complete flow with 3-5 real users
2. Verify Redis persistence across restarts
3. Deploy to Railway with Redis addon
4. Monitor first live conversations
5. Quick fixes based on real usage

---

## 🤔 STATE MACHINE COMPLEXITY ANALYSIS

### Option 1: Simple Dictionary (THIS WEEK) ✅
**Complexity: Low | Time: 2 hours | Walkback Risk: None**
```python
conversation_states = {
    "+1234567890": {
        "status": "analyzing",
        "last_analysis": {...},
        "timestamp": datetime.now()
    }
}
```
- **Pros**: Ships this week, easy to debug, no dependencies
- **Cons**: Lost on server restart, no history
- **Verdict**: START HERE

### Option 2: Redis + Structured State (WEEK 2) 🔧
**Complexity: Medium | Time: 4-6 hours | Walkback Risk: Low**
```python
class ConversationManager:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def get_state(self, phone):
        return json.loads(self.redis.get(f"state:{phone}") or "{}")
```
- **Pros**: Survives restarts, can track history
- **Cons**: Needs Redis setup, more complex
- **Verdict**: Natural evolution from Option 1

### Option 3: Full State Machine (WEEK 3-4) 🚀
**Complexity: High | Time: 8-12 hours | Walkback Risk: Medium**
```python
class ConversationFSM:
    # Full implementation from refactoring doc
```
- **Pros**: Handles all edge cases, clear flow
- **Cons**: Over-engineered for MVP, harder to modify
- **Verdict**: Wait until you have real user patterns

## 📁 DOCUMENTATION STRUCTURE

```
docs/
├── IMPLEMENTATION_PLAN_WEEK1.md (this file)
├── ONBOARDING_SYSTEM.md ✅
├── system_gap_analysis.md ✅
├── updated_business_flow.md ✅
├── refactoring_opportunities.md ✅
├── WEEK2_PLAN.md (to be created)
└── NORMAN_PRINCIPLES_ROADMAP.md (future)
```

## ✅ SUCCESS CRITERIA

By Friday evening, you should have:
1. Real cart data feeding meal plans
2. User preferences influencing recommendations
3. Basic conversation state (remembers last analysis)
4. Help text guiding users
5. PDF recipes generating
6. Modification commands working (swap/skip/remove)
7. Deployed and tested with real users

## 🚫 DO NOT ATTEMPT THIS WEEK
- Complex state machines
- Redis setup
- Web interface
- Natural language processing
- Preference evolution
- Multi-modal interfaces

## 🎯 KEY PRINCIPLE
**Every change is additive** - Nothing breaks, everything builds on what works.

---

*Remember: Ship this week, iterate toward excellence. The perfect is the enemy of the good.*