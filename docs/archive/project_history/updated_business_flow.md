# 📱 Farm to People Updated Business Flow
*Based on new requirements - High protein focus, confirmation flow, meal calendar*

## 🎯 KEY REQUIREMENT UPDATES

### **Protein Requirements:**
- **Women:** 30g minimum per meal
- **Men:** 35-40g minimum per meal
- Adjust based on household composition

### **Model Update:**
- Switch to GPT-5 (when available)
- Currently using GPT-4 as placeholder

### **Timing Strategy:**
- Cart analysis immediately after "plan"
- Recipe generation after confirmation OR day before delivery
- Allow modifications until FTP order locks

---

## 📊 UPDATED SMS FLOW

### **1️⃣ INITIAL REQUEST**
**Trigger:** User texts "plan"
**Response:** Comprehensive cart analysis (not just meal ideas)

---

### **2️⃣ COMPREHENSIVE CART ANALYSIS**

```
📦 YOUR CART ANALYSIS
Total: $127.50 | Delivery: Sunday 8/28

CURRENT ITEMS:
✅ Proteins (2 items)
   • Eggs (1 dozen) - Good for 3 meals
   • Need: +3-4 protein sources

🥬 Vegetables (9 items)
   • Eggplant, Zucchini, Tomatoes, Peppers
   • Carrots, Lettuce, Corn, Potatoes

🍎 Fruits (5 items)
   • Peaches, Plums, Apples, Avocados

📊 MEAL COVERAGE:
Based on your preferences (Dinner + Lunch for 2):

     | Mon | Tue | Wed | Thu | Fri | Sat | Sun |
-----|-----|-----|-----|-----|-----|-----|-----|
Lunch|  ❌  |  ❌  |  ❌  |  ❌  |  ❌  |  ⚠️  |  ⚠️  |
Din. |  ✅  |  ✅  |  ✅  |  ⚠️  |  ⚠️  |  ❌  |  ❌  |

✅ = Covered | ⚠️ = Partial | ❌ = Need protein

🔄 RECOMMENDED SWAPS:
1. Swap: 1 Peach → Red Onions (Mediterranean essential)
2. Swap: Lunchbox → Fresno Peppers (better for stir-fry)

🥩 PROTEIN ADDITIONS NEEDED:
For your HIGH-PROTEIN goals (30g+ per meal):
• Wild Salmon (3 fillets) +$24
• Chicken Breast (3 lbs) +$21  
• Ground Turkey (2 lbs) +$18
TOTAL ADDITIONS: +$63

💡 MEAL PREVIEW:
With additions, you can make:
• Mediterranean Chicken Bowls (35g protein)
• Salmon Ratatouille (32g protein)
• Turkey Veggie Stir-fry (38g protein)
• High-Protein Egg Scrambles (30g protein)

Reply:
- CONFIRM to accept ($190.50 total)
- REMOVE [item] to delete items
- SWAP [X for Y] to substitute
- SKIP [day] if not cooking
```

---

### **3️⃣ CUSTOMIZATION OPTIONS**

#### **A. Skip Days**
```
User: "SKIP Thursday Friday"
System: "Got it! Removing Thu/Fri from meal plan.
        Adjusting portions for 10 meals (5 days).
        New protein needs: 2 lbs chicken, 2 salmon"
```

#### **B. Item Removal**
```
User: "REMOVE eggplant"
System: "Removed eggplant. Updating meal options...
        Replaced ratatouille with sheet pan vegetables"
```

#### **C. Swaps**
```
User: "SWAP salmon for more chicken"  
System: "Swapped! 3 salmon → 2 lbs chicken
        All meals now poultry-based
        Protein still 30g+ per meal"
```

---

### **4️⃣ CONFIRMATION FLOW**

```
User: "CONFIRM"

System: "✅ Order confirmed at $190.50!

📅 RECIPE DELIVERY:
Your detailed recipes with full instructions 
will be sent Saturday morning (day before delivery).

🔔 You'll receive:
- Complete PDF recipe guide
- Shopping checklist 
- Prep schedule
- Storage instructions

Want recipes earlier? Reply 'RECIPES NOW'"
```

---

### **5️⃣ RECIPE GENERATION TIMING**

#### **Option A: Immediate (if requested)**
```
User: "RECIPES NOW"
System: [Generates and sends full recipe PDF]
```

#### **Option B: Day Before Delivery (default)**
- Saturday 8am for Sunday delivery
- Allows maximum modification time
- Sent automatically via scheduled task

---

## 📊 MEAL CALENDAR VISUALIZATION

### **Enhanced Calendar Display**
```
📅 YOUR MEAL PLAN (Aug 26 - Sep 1)

PLANNED MEALS (✅ = ingredients confirmed)
════════════════════════════════════════════
     | Mon 26 | Tue 27 | Wed 28 | Thu 29 | Fri 30 |
-----|--------|--------|--------|--------|--------|
🌅 L | Egg Bowl| Turkey | Chicken| SKIP   | SKIP   |
     | ✅ 30g  | ✅ 35g  | ✅ 32g  |        |        |
-----|--------|--------|--------|--------|--------|  
🌙 D | Salmon | Stir-fry| Bowls  | SKIP   | SKIP   |
     | ✅ 35g  | ✅ 38g  | ✅ 35g  |        |        |

PROTEIN TRACKER: Avg 34g/meal ✅ (Goal: 30g+)
INGREDIENTS: 95% covered ⚠️ (need herbs)
```

---

## 🔄 ITERATIVE REFINEMENT FLOW

### **Multi-Round Conversation**
```
Round 1:
User: "plan"
System: [Comprehensive analysis]

Round 2:  
User: "I don't like eggplant"
System: "Removing eggplant, updating meals..."

Round 3:
User: "Add more chicken"
System: "Adding 2 lbs chicken breast..."

Round 4:
User: "CONFIRM"
System: "Order confirmed!"
```

### **Smart Inquiries**
- System proactively asks about constraints
- Learns from modifications for next week
- Stores preferences for evolution

---

## 💪 HIGH-PROTEIN MEAL SPECIFICATIONS

### **Protein Calculations**
```python
def calculate_protein_target(user):
    base = 30  # Women baseline
    if user.gender == "male":
        base = 35
    if user.activity_level == "high":
        base += 5
    if user.goal == "muscle_building":
        base += 10
    return base

# Example meals meeting targets:
meals = {
    "Mediterranean Bowl": {
        "protein_sources": ["chicken_breast_6oz", "feta_2oz", "chickpeas_1cup"],
        "total_protein": 42,
        "meets_target": True
    },
    "Salmon Ratatouille": {
        "protein_sources": ["salmon_5oz", "white_beans_0.5cup"],  
        "total_protein": 35,
        "meets_target": True
    }
}
```

---

## 📱 IMPLEMENTATION UPDATES NEEDED

### **1. Cart Analysis Enhancement**
```python
# server/meal_planner.py
def generate_comprehensive_analysis(cart_data, user_prefs):
    analysis = {
        "cart_summary": summarize_cart(cart_data),
        "meal_calendar": generate_calendar(user_prefs),
        "coverage_gaps": identify_gaps(cart_data, user_prefs),
        "protein_analysis": calculate_protein_needs(user_prefs),
        "smart_swaps": suggest_swaps(cart_data, user_prefs),
        "meal_preview": preview_possible_meals(cart_data)
    }
    return format_for_sms(analysis)
```

### **2. Conversation State Management**
```python
# server/server.py
conversation_states = {}

async def handle_sms(phone, message):
    state = conversation_states.get(phone, "new")
    
    if "plan" in message:
        state = "analysis_sent"
        send_comprehensive_analysis()
    
    elif state == "analysis_sent":
        if "confirm" in message:
            state = "confirmed"
            schedule_recipe_delivery()
        elif "skip" in message:
            update_meal_calendar()
        elif "swap" in message:
            process_swap()
            regenerate_analysis()
    
    conversation_states[phone] = state
```

### **3. Calendar Generation**
```python
def generate_meal_calendar(user_prefs, cart_items):
    calendar = {}
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    meals = user_prefs["meal_timing"]  # ["lunch", "dinner"]
    
    for day in days:
        calendar[day] = {}
        for meal in meals:
            calendar[day][meal] = {
                "planned": get_meal_for_day(day, meal),
                "protein": calculate_protein(meal),
                "covered": check_ingredients(cart_items)
            }
    
    return format_calendar_table(calendar)
```

### **4. Recipe Delivery Scheduler**
```python
# New file: server/scheduler.py
import schedule
import time
from datetime import datetime, timedelta

def schedule_recipe_delivery(user, delivery_date):
    send_date = delivery_date - timedelta(days=1)
    send_time = "08:00"
    
    schedule.every().day.at(send_time).do(
        send_recipe_pdf, user=user
    ).tag(f"recipes_{user.id}")
    
    # Also store in database for persistence
    save_scheduled_task(user.id, send_date, send_time)
```

---

## 🎯 SUCCESS METRICS

### **Updated KPIs**
- **Protein Target Achievement:** 95% of meals meet minimum
- **Confirmation Rate:** 80% confirm on first analysis
- **Modification Rate:** 30% make at least one change
- **Skip Day Usage:** 20% customize their calendar
- **Recipe Request Timing:** 60% wait for auto-delivery

---

## 🚀 DEPLOYMENT REQUIREMENTS

### **Technical Updates**
1. Upgrade to GPT-5 when available (currently GPT-4)
2. Implement conversation state management
3. Add calendar visualization formatter
4. Build recipe scheduling system
5. Create modification handlers (skip/swap/remove)

### **Database Updates**
```sql
-- Add conversation state table
conversation_state {
    phone_number
    current_state
    cart_snapshot
    modifications[]
    confirmed_at
    recipe_scheduled_for
}

-- Add meal calendar table  
meal_calendar {
    user_id
    week_of
    planned_meals{}
    skipped_days[]
    actual_meals_cooked{}
}
```

---

*This updated flow emphasizes comprehensive cart analysis, high-protein requirements, flexible timing, and iterative refinement through conversation.*