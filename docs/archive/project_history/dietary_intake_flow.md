# Dietary Intake Flow - Enhanced SMS Onboarding

## Overview
Comprehensive documentation for the "FEED ME" onboarding flow that combines Farm to People credential collection with AI-powered dietary preference gathering.

## Complete User Journey

### 1. Initial Trigger
**User texts:** `"FEED ME"`

**System Logic:**
```python
elif "feed me" in user_message.lower():
    user_data = db.get_user_by_phone(user_phone_number)
    
    if not user_data or not user_data.get('ftp_email'):
        # No credentials yet - start with login
        login_link = f"{base_url}/login?phone={quote(user_phone_number)}&flow=intake"
        reply = "Welcome! Let's get you set up with personalized meal planning. First, connect your Farm to People account: " + login_link
    elif not user_data.get('preferences', {}).get('setup_completed'):
        # Has credentials, needs dietary intake
        reply = "Welcome back! Let's personalize your meal plans. Tell me about your dietary needs! Any allergies, diet preferences, or foods you avoid? (Example: 'allergic to nuts, vegetarian, hate mushrooms' or just 'none')"
        db.set_user_intake_state(user_phone_number, "waiting_dietary_info")
    else:
        # Fully set up already
        reply = "You're all set! Text 'plan' for meal ideas or 'preferences' to update your settings."
```

### 2. Credential Collection (Web Form)
**Enhanced Login Form:**
- URL includes `?flow=intake` parameter
- After successful credential save, triggers SMS continuation
- Redirect message: "Great! Your account is connected. Check your phone for a few quick questions to personalize your meal plans."

**Enhanced Login Handler:**
```python
@app.post("/login")
async def login_submit(phone: str = Form(""), email: str = Form(...), password: str = Form(...), request: Request):
    flow_type = request.query_params.get("flow", "normal")
    
    try:
        db.upsert_user_credentials(phone_number=phone, ftp_email=email, ftp_password=password)
        
        if flow_type == "intake" and phone:
            # Trigger SMS intake flow
            await trigger_dietary_intake_sms(phone)
            return PlainTextResponse("Great! Your account is connected. Check your phone for a few quick questions to personalize your meal plans.")
        else:
            return PlainTextResponse("Saved. You can now text 'plan' to get meal ideas.")
    except Exception as e:
        return PlainTextResponse("Error saving info. Please try again.", status_code=500)

async def trigger_dietary_intake_sms(phone_number: str):
    """Send the first dietary intake question after credential submission"""
    reply = "Perfect! Your Farm to People account is connected. Now let's personalize your meal plans. Tell me about your dietary needs! Any allergies, diet preferences, or foods you avoid? (Example: 'allergic to nuts, vegetarian, hate mushrooms' or just 'none')"
    
    db.set_user_intake_state(phone_number, "waiting_dietary_info")
    await send_sms(phone_number, reply)
```

### 3. Dietary Information Collection

#### Single Broad Question Strategy
**Question:** "Tell me about your dietary needs! Any allergies, diet preferences, or foods you avoid? (Example: 'allergic to nuts, vegetarian, hate mushrooms' or just 'none')"

#### AI-Powered Response Parsing
```python
async def parse_dietary_info_with_ai(user_response: str) -> dict:
    """Parse natural language dietary response using GPT-4"""
    prompt = f"""
    Parse this dietary response into structured data:
    User said: "{user_response}"
    
    Extract and return JSON with:
    {{
        "allergies": ["nuts", "dairy"],  // Serious medical allergies only
        "diet_type": "vegetarian",       // vegetarian, vegan, pescatarian, keto, paleo, or null
        "dislikes": ["mushrooms"],       // Foods they don't like but aren't allergic to
        "confidence": "high",            // high, medium, low
        "needs_clarification": []        // Questions to ask for clarity
    }}
    
    Rules:
    - Only mark as allergy if they use words like "allergic", "allergy", "can't eat"
    - Diet types: vegetarian, vegan, pescatarian, keto, paleo, gluten-free
    - Dislikes are preferences, not medical needs
    - High confidence = clear, unambiguous response
    - Low confidence = vague or unclear
    """
    
    response = await openai_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.1  # Lower temperature for consistent parsing
    )
    
    return json.loads(response.choices[0].message.content)
```

#### Response Handling Logic
```python
async def handle_dietary_intake(phone_number: str, response: str):
    """Process dietary information response with AI parsing"""
    parsed = await parse_dietary_info_with_ai(response)
    
    if parsed["confidence"] == "high" and not parsed["needs_clarification"]:
        # Clear response - store and continue
        save_partial_preferences(phone_number, parsed)
        reply = f"Perfect! I've got: {format_preferences_summary(parsed)}. How much time do you usually have for cooking? Reply: Quick (15min), Standard (30min), or Love cooking (45min+)"
        db.set_user_intake_state(phone_number, "waiting_cooking_time")
        
    elif parsed["confidence"] == "low" or parsed["needs_clarification"]:
        # Needs clarification
        clarification = " ".join(parsed["needs_clarification"]) if parsed["needs_clarification"] else "Could you be more specific about your dietary needs?"
        reply = f"Got it! Just to clarify - {clarification}"
        db.set_user_intake_state(phone_number, "waiting_clarification", parsed)
        
    else:
        # Medium confidence - confirm before proceeding
        summary = format_preferences_summary(parsed)
        reply = f"Thanks! Just to confirm: {summary}. Sound right? (yes/no)"
        db.set_user_intake_state(phone_number, "waiting_confirmation", parsed)
    
    return reply
```

### 4. Cooking Time Collection
**Question:** "How much time do you usually have for cooking? Reply: Quick (15min), Standard (30min), or Love cooking (45min+)"

**Simple Parsing:**
```python
def parse_cooking_time(response: str) -> str:
    """Parse cooking time preference"""
    response = response.lower()
    if any(word in response for word in ['quick', '15', 'fast', 'short']):
        return 'quick'
    elif any(word in response for word in ['love', '45', 'long', 'enjoy']):
        return 'all_in'
    else:
        return 'standard'  # Default
```

### 5. Completion & Storage
**Final Message:** "All set! 🎉 Text 'plan' anytime for meal ideas based on your Farm to People cart!"

**Data Storage Structure:**
```json
{
  "preferences": {
    "allergies": ["nuts", "shellfish"],
    "diet_type": "vegetarian", 
    "dislikes": ["beets", "mushrooms"],
    "cooking_time": "standard",
    "raw_dietary_input": "allergic to nuts and shellfish, vegetarian, hate beets and mushrooms",
    "setup_completed": true,
    "setup_date": "2025-08-22T10:30:00Z"
  },
  "intake_state": null,  // Clear after completion
  "intake_data": {}      // Clear after completion
}
```

## Example User Interactions

### Example 1: Clear Response
**User:** "allergic to nuts, vegetarian, hate mushrooms"
**AI Parsing:** 
```json
{
  "allergies": ["nuts"], 
  "diet_type": "vegetarian",
  "dislikes": ["mushrooms"],
  "confidence": "high"
}
```
**Response:** "Perfect! Vegetarian, allergic to nuts, no mushrooms. How much time for cooking? Quick (15min), Standard (30min), or Love cooking (45min+)?"

### Example 2: Needs Clarification
**User:** "I don't eat meat but fish is ok"
**AI Parsing:**
```json
{
  "diet_type": "pescatarian",
  "confidence": "medium", 
  "needs_clarification": ["Are dairy and eggs okay?"]
}
```
**Response:** "Got it - you eat fish but no meat! Just to clarify - Are dairy and eggs okay?"

### Example 3: Vague Response
**User:** "kinda healthy I guess"
**AI Parsing:**
```json
{
  "confidence": "low",
  "needs_clarification": ["What does healthy mean to you - less meat, more vegetables, avoid processed foods?"]
}
```
**Response:** "Got it! Just to clarify - What does healthy mean to you - less meat, more vegetables, avoid processed foods?"

## Database Schema Updates

### User Table Additions:
```sql
ALTER TABLE users ADD COLUMN intake_state TEXT;
ALTER TABLE users ADD COLUMN intake_data JSONB DEFAULT '{}';
```

### Required Functions in supabase_client.py:
```python
def set_user_intake_state(phone_number: str, state: str, data: dict = None)
def get_user_intake_state(phone_number: str) -> tuple  # Returns (state, data)
def save_partial_preferences(phone_number: str, preferences: dict)
def finalize_user_preferences(phone_number: str, final_data: dict)
```

## Integration with Meal Planning

### Enhanced meal_planner.py Usage:
```python
def run_main_planner_with_user_prefs(phone_number: str):
    """Run meal planner with user's stored preferences"""
    user_data = db.get_user_by_phone(phone_number)
    user_prefs = user_data.get("preferences", {}) if user_data else {}
    
    # Convert preferences to meal planner format
    diet_hard = user_prefs.get("allergies", [])
    if user_prefs.get("diet_type"):
        diet_hard.append(user_prefs["diet_type"])
    
    dislikes = user_prefs.get("dislikes", [])
    time_mode = user_prefs.get("cooking_time", "standard")
    
    # Get cart data and generate meal plan
    latest_cart_file = get_latest_cart_file(FARM_BOX_DATA_DIR)
    if not latest_cart_file:
        return {"error": "Could not find cart data."}
        
    with open(latest_cart_file, 'r') as f:
        cart_data = json.load(f)
        
    all_ingredients = get_all_ingredients_from_cart(cart_data, FARM_BOX_DATA_DIR)
    master_product_list = get_master_product_list(PRODUCT_CATALOG_FILE)
    
    meal_plan = generate_meal_plan(
        all_ingredients, master_product_list,
        diet_hard=diet_hard, 
        dislikes=dislikes, 
        time_mode=time_mode
    )
    
    return meal_plan
```

## Implementation Priority

1. **Phase 1:** Update login form to support `?flow=intake` parameter
2. **Phase 2:** Add intake state management to database and supabase_client.py
3. **Phase 3:** Implement AI parsing for dietary responses
4. **Phase 4:** Create complete SMS routing for intake flow
5. **Phase 5:** Integration testing with real user flows

## Benefits

- **Natural Language**: Users can express complex dietary needs naturally
- **AI-Powered**: Handles nuanced responses like "plant-based but eat fish"
- **Efficient**: Most users complete setup in 2-3 messages
- **Accurate**: Clarifies when uncertain, especially for allergies
- **Seamless**: Bridges web credential collection with SMS preferences
- **Personalized**: Rich preference data improves meal plan quality

This approach provides a sophisticated yet user-friendly onboarding experience that collects comprehensive dietary information while maintaining the simplicity of SMS interaction.