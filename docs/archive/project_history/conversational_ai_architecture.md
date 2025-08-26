# Conversational AI Architecture - Friend Flow Design

## Overview
Design for enhanced SMS-based conversational AI that maintains context between messages while integrating with existing Farm to People meal planning functionality.

## Current SMS Flow: Vonage → Railway → OpenAI

### 1. Vonage Webhook → Railway
```json
POST /sms/incoming
{
  "msisdn": "14255551234",
  "text": "Hello",
  "to": "18339439183"
}
```

### 2. Current Message Routing (server.py:175-202)
```python
if "hello" in user_message:
    reply = "Hi there! I'm your Farm to People meal planning assistant. How can I help?"
elif "plan" in user_message:
    # Background meal planning task
elif "new" in user_message:
    # Registration flow
else:
    reply = "Sorry, I didn't understand that. Text 'plan' for meal ideas."
```

### 3. Current OpenAI Integration (meal_planner.py)
- Only used for meal planning
- Single-shot prompts (no conversation context)
- Cart data + preferences → recipes

## Proposed Enhanced Architecture

### Database Schema Addition

```sql
-- New table for conversation management
CREATE TABLE conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    phone_number TEXT NOT NULL,
    conversation_state TEXT DEFAULT 'active', -- active, paused, ended
    context_type TEXT DEFAULT 'general', -- general, cart_planning, order_questions
    last_cart_data JSONB, -- Cache latest cart for context
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- New table for message history
CREATE TABLE conversation_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL, -- 'user', 'assistant', 'system'
    content TEXT NOT NULL,
    metadata JSONB, -- Cart data, preferences, etc.
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_conversations_phone ON conversations(phone_number);
CREATE INDEX idx_conversations_state ON conversations(conversation_state);
CREATE INDEX idx_messages_conversation ON conversation_messages(conversation_id, created_at);
```

### Enhanced Message Routing Logic

```python
# Enhanced routing in sms_incoming()
async def sms_incoming(request: Request, background_tasks: BackgroundTasks, ...):
    # ... [existing parsing logic] ...
    
    # Check for active conversation
    active_conversation = get_active_conversation(user_phone_number)
    
    # Command routing vs conversational mode
    if is_command(user_message):  # "plan", "new", "stop", "help"
        if user_message.lower().strip() == "stop conversation":
            end_conversation(user_phone_number)
            reply = "Conversation ended. Text 'hello' to start again."
        elif "plan" in user_message:
            # Traditional meal planning flow
            reply = "Preparing your meal plan..."
            background_tasks.add_task(run_full_meal_plan_flow, user_phone_number)
        # ... other commands ...
    elif active_conversation:
        # CONVERSATIONAL MODE - send to AI with context
        reply = await handle_conversational_message(
            user_phone_number, user_message, active_conversation
        )
    elif "hello" in user_message.lower():
        # Start new conversation
        conversation_id = start_new_conversation(user_phone_number)
        reply = await handle_conversational_message(
            user_phone_number, user_message, {"id": conversation_id}
        )
    else:
        # Default fallback
        reply = "Text 'hello' to chat about your order, or 'plan' for meal ideas."
```

### Context Injection Strategy

```python
async def handle_conversational_message(phone_number: str, message: str, conversation: dict) -> str:
    """
    Send user message + full context to OpenAI for intelligent response
    """
    # 1. Load conversation history (last 10 messages for context window)
    message_history = get_conversation_messages(conversation["id"], limit=10)
    
    # 2. Load user's current cart data (if available)
    user_data = db.get_user_by_phone(phone_number)
    cart_data = get_latest_cart_for_user(user_data) if user_data else None
    
    # 3. Build context-rich prompt
    system_prompt = build_system_prompt(cart_data, user_data)
    conversation_messages = build_conversation_context(message_history)
    
    # 4. Send to OpenAI
    messages = [
        {"role": "system", "content": system_prompt},
        *conversation_messages,
        {"role": "user", "content": message}
    ]
    
    response = await openai_client.chat.completions.create(
        model="gpt-4",  # Better for conversation than gpt-5-mini
        messages=messages,
        max_tokens=150,  # Keep SMS-friendly
        temperature=0.7
    )
    
    ai_reply = response.choices[0].message.content
    
    # 5. Store both messages in conversation history
    store_conversation_message(conversation["id"], "user", message)
    store_conversation_message(conversation["id"], "assistant", ai_reply, 
                              metadata={"cart_data": cart_data})
    
    return ai_reply

def build_system_prompt(cart_data: dict, user_data: dict) -> str:
    """Build context-aware system prompt"""
    base_prompt = """You are a friendly Farm to People meal planning assistant. 
    You help customers with questions about their orders via SMS.
    
    Keep responses under 160 characters when possible.
    Be conversational but helpful.
    """
    
    if cart_data:
        items = [item.get("name", "") for item in cart_data.get("items", [])]
        base_prompt += f"\n\nCURRENT CART: {', '.join(items)}"
    
    if user_data and user_data.get("preferences"):
        prefs = user_data["preferences"]
        base_prompt += f"\n\nUSER PREFERENCES: {prefs}"
    
    return base_prompt
```

## Required Code Changes

### New Files to Create:
```
server/
├── conversation_manager.py      # Core conversation logic
├── ai_chat_handler.py          # OpenAI integration for chat
└── migrations/
    └── 001_add_conversations.sql # Database schema

tests/
├── test_conversation_flow.py   # Integration tests
└── test_ai_responses.py       # AI response validation
```

### Files to Modify:

**1. `server/supabase_client.py`** - Add conversation database functions:
```python
# Add these functions:
def start_conversation(phone_number: str, context_type: str = "general") -> str
def get_active_conversation(phone_number: str) -> Optional[dict]
def store_conversation_message(conversation_id: str, role: str, content: str, metadata: dict = None)
def get_conversation_messages(conversation_id: str, limit: int = 10) -> List[dict]
def end_conversation(phone_number: str)
```

**2. `server/server.py`** - Replace message routing logic

**3. `requirements.txt`** - Add dependencies if needed

## Example Conversation Flow

**User:** "Hello"
**System:** Creates new conversation, sends to OpenAI with system prompt
**AI:** "Hi! I'm your Farm to People assistant. I can help with your current order, suggest recipes, or answer questions. What would you like to know?"

**User:** "What's in my current cart?"
**System:** Loads conversation history + cart data, builds context-rich prompt
**AI:** "You have organic kale, chicken thighs, and seasonal apples. Want recipe ideas using these ingredients?"

**User:** "Yes, something quick"
**System:** Full context (cart + conversation + "quick" preference)
**AI:** "Try this 15-min dish: Pan-seared chicken with wilted kale and apple slices. Want the full recipe?"

## Implementation Priority

1. **Phase 1:** Database schema + basic conversation storage
2. **Phase 2:** Enhanced message routing (command vs chat detection)  
3. **Phase 3:** OpenAI integration with context injection
4. **Phase 4:** Testing with real cart data integration

## Key Benefits

1. **Stateful Conversations** - Users can ask follow-up questions naturally
2. **Cart-Aware Responses** - AI knows their current order contents  
3. **Mixed Mode Support** - Can switch between chat and commands seamlessly
4. **SMS-Optimized** - Responses kept concise for text messaging
5. **Scalable Context** - Database storage allows complex conversation flows

---

**Note:** This is a future enhancement. Current focus should be on core functionality: login → scrape → meal plans with dietary intake.