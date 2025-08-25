# 🔄 Redis + Structured State Management Implementation

## 📋 Overview
Implementing Redis-backed conversation state management for persistent, scalable SMS conversations. This will be tackled **Wednesday** after core connections are working.

### **THE KEY BENEFIT: Never Lose Context**
When you push updates or restart your server:
- ✅ Conversations continue exactly where they left off
- ✅ Users don't have to start over
- ✅ Modifications and analysis are preserved
- ✅ No "sorry, I forgot what we were talking about" moments

---

## 🏗️ Architecture

### **Why Redis?**
- **Persistence**: Survives server restarts
- **TTL Support**: Auto-expire old conversations
- **Fast**: In-memory with disk backup
- **Scalable**: Ready for multiple servers
- **Simple**: Key-value perfect for phone → state mapping

### **Data Structure**
```python
# Key format: "conversation:{phone_number}"
# Value: JSON-serialized conversation state
# TTL: 2 hours (renewable on activity)

{
    "phone": "+1234567890",
    "status": "analysis_sent",
    "created_at": "2024-08-26T10:30:00",
    "last_activity": "2024-08-26T10:35:00",
    "context": {
        "last_analysis": {...},
        "cart_snapshot": {...},
        "user_preferences": {...},
        "modifications": [
            {"type": "swap", "details": {...}, "timestamp": "..."},
            {"type": "skip", "details": {...}, "timestamp": "..."}
        ],
        "confirmation_status": null,
        "recipes_sent": false
    },
    "metrics": {
        "message_count": 5,
        "error_count": 0,
        "analysis_count": 1
    }
}
```

---

## 💻 Implementation (Wednesday - 4 hours)

### **Phase 1: Redis Setup (30 mins)**

```python
# server/redis_client.py
import redis
import json
from typing import Optional, Dict, Any
from datetime import datetime

class ConversationStore:
    def __init__(self, redis_url: str = None):
        self.redis = redis.from_url(
            redis_url or os.getenv('REDIS_URL', 'redis://localhost:6379'),
            decode_responses=True
        )
        self.ttl = 7200  # 2 hours
    
    def get_state(self, phone: str) -> Optional[Dict]:
        """Retrieve conversation state"""
        key = f"conversation:{phone}"
        data = self.redis.get(key)
        if data:
            return json.loads(data)
        return None
    
    def set_state(self, phone: str, state: Dict) -> None:
        """Save conversation state with TTL"""
        key = f"conversation:{phone}"
        state['last_activity'] = datetime.now().isoformat()
        self.redis.setex(
            key,
            self.ttl,
            json.dumps(state)
        )
    
    def update_status(self, phone: str, status: str) -> None:
        """Quick status update"""
        state = self.get_state(phone) or self._create_new_state(phone)
        state['status'] = status
        self.set_state(phone, state)
    
    def add_modification(self, phone: str, mod_type: str, details: Dict) -> None:
        """Track user modifications"""
        state = self.get_state(phone)
        if state:
            state['context']['modifications'].append({
                'type': mod_type,
                'details': details,
                'timestamp': datetime.now().isoformat()
            })
            self.set_state(phone, state)
    
    def _create_new_state(self, phone: str) -> Dict:
        """Initialize new conversation"""
        return {
            'phone': phone,
            'status': 'idle',
            'created_at': datetime.now().isoformat(),
            'last_activity': datetime.now().isoformat(),
            'context': {
                'last_analysis': None,
                'cart_snapshot': None,
                'user_preferences': None,
                'modifications': [],
                'confirmation_status': None,
                'recipes_sent': False
            },
            'metrics': {
                'message_count': 0,
                'error_count': 0,
                'analysis_count': 0
            }
        }
```

### **Phase 2: Conversation Manager (1.5 hours)**

```python
# server/conversation_manager.py
from enum import Enum
from typing import Optional, Dict, Any
import logging

class ConversationStatus(Enum):
    IDLE = "idle"
    ANALYZING = "analyzing"
    ANALYSIS_SENT = "analysis_sent"
    MODIFYING = "modifying"
    CONFIRMED = "confirmed"
    RECIPES_SENT = "recipes_sent"
    ERROR = "error"

class ConversationManager:
    def __init__(self, store: ConversationStore):
        self.store = store
        self.logger = logging.getLogger(__name__)
    
    async def process_message(self, phone: str, message: str, user_data: Dict = None) -> Dict:
        """Main entry point for processing messages"""
        
        # Get or create conversation state
        state = self.store.get_state(phone)
        if not state:
            state = self.store._create_new_state(phone)
            if user_data:
                state['context']['user_preferences'] = user_data.get('preferences', {})
            self.store.set_state(phone, state)
        
        # Increment message count
        state['metrics']['message_count'] += 1
        
        # Classify intent based on message AND current state
        intent = self.classify_intent(message, state['status'])
        
        # Route to appropriate handler
        response = await self.route_message(phone, message, intent, state)
        
        # Save updated state
        self.store.set_state(phone, state)
        
        return {
            'response': response,
            'state': state['status'],
            'intent': intent
        }
    
    def classify_intent(self, message: str, current_status: str) -> str:
        """Smart intent classification based on context"""
        message_lower = message.lower()
        
        # State-specific intent detection
        if current_status == ConversationStatus.ANALYSIS_SENT.value:
            if any(word in message_lower for word in ['yes', 'confirm', 'good', 'perfect']):
                return 'confirm'
            elif 'swap' in message_lower or 'replace' in message_lower:
                return 'swap'
            elif 'skip' in message_lower or 'remove' in message_lower:
                return 'skip'
            elif 'no' in message_lower or 'change' in message_lower:
                return 'modify'
        
        # Global intents (work from any state)
        if any(word in message_lower for word in ['plan', 'meal', 'analyze']):
            return 'request_plan'
        elif 'help' in message_lower or '?' in message_lower:
            return 'help'
        elif any(word in message_lower for word in ['start over', 'restart', 'reset']):
            return 'reset'
        elif 'recipe' in message_lower and 'now' in message_lower:
            return 'recipes_now'
        
        return 'unknown'
    
    async def route_message(self, phone: str, message: str, intent: str, state: Dict) -> str:
        """Route to appropriate handler based on intent and state"""
        
        current_status = state['status']
        
        # Handle global intents first
        if intent == 'reset':
            return await self.handle_reset(phone, state)
        elif intent == 'help':
            return self.generate_help_message(current_status)
        
        # State-specific routing
        if intent == 'request_plan':
            if current_status in [ConversationStatus.IDLE.value, ConversationStatus.ERROR.value]:
                state['status'] = ConversationStatus.ANALYZING.value
                state['metrics']['analysis_count'] += 1
                return "📦 Analyzing your Farm to People cart..."
            else:
                return "⏳ Already working on your meal plan. One moment..."
        
        elif current_status == ConversationStatus.ANALYSIS_SENT.value:
            if intent == 'confirm':
                state['status'] = ConversationStatus.CONFIRMED.value
                state['context']['confirmation_status'] = 'confirmed'
                return "✅ Perfect! Generating your detailed recipes..."
            
            elif intent == 'swap':
                state['status'] = ConversationStatus.MODIFYING.value
                swap_details = self.parse_swap_request(message)
                self.store.add_modification(phone, 'swap', swap_details)
                return f"🔄 Swapping {swap_details.get('old')} for {swap_details.get('new')}..."
            
            elif intent == 'skip':
                state['status'] = ConversationStatus.MODIFYING.value
                skip_details = self.parse_skip_request(message)
                self.store.add_modification(phone, 'skip', skip_details)
                days = skip_details.get('days', [])
                return f"📅 Removing {', '.join(days)} from your meal plan..."
        
        elif current_status == ConversationStatus.CONFIRMED.value:
            if intent == 'recipes_now':
                state['status'] = ConversationStatus.RECIPES_SENT.value
                state['context']['recipes_sent'] = True
                return "📧 Sending your recipe PDF now..."
        
        # Default response with guidance
        return self.generate_default_response(current_status)
    
    def generate_help_message(self, current_status: str) -> str:
        """Context-aware help messages"""
        help_messages = {
            ConversationStatus.IDLE.value: """
📚 Here's what I can do:
• Text 'plan' - Get personalized meal plan
• Text 'help' - See this message
• Text 'new' - Set up your account
""",
            ConversationStatus.ANALYSIS_SENT.value: """
📚 Your meal plan is ready! You can:
• Reply 'yes' - Confirm and get recipes
• Reply 'swap X for Y' - Change ingredients
• Reply 'skip Monday' - Remove days
• Reply 'help' - See options
""",
            ConversationStatus.CONFIRMED.value: """
📚 Order confirmed! You can:
• Reply 'recipes now' - Get recipes immediately
• Wait for automatic delivery (day before)
• Reply 'help' - See options
"""
        }
        return help_messages.get(current_status, help_messages[ConversationStatus.IDLE.value])
    
    def parse_swap_request(self, message: str) -> Dict:
        """Extract swap details from message"""
        # Simple parsing - can be enhanced
        import re
        pattern = r'swap\s+(\w+)\s+for\s+(\w+)'
        match = re.search(pattern, message.lower())
        if match:
            return {'old': match.group(1), 'new': match.group(2)}
        return {'old': 'unknown', 'new': 'unknown'}
    
    def parse_skip_request(self, message: str) -> Dict:
        """Extract skip days from message"""
        days = []
        day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        message_lower = message.lower()
        for day in day_names:
            if day in message_lower:
                days.append(day.capitalize())
        return {'days': days}
```

### **Phase 3: Integration with Server (1.5 hours)**

```python
# server/server.py - Updated webhook handler
from conversation_manager import ConversationManager
from redis_client import ConversationStore

# Initialize once at startup
conversation_store = ConversationStore()
conversation_manager = ConversationManager(conversation_store)

@app.post("/webhook/sms")
async def handle_sms_webhook(request: Request, background_tasks: BackgroundTasks):
    data = await request.form()
    phone = data.get('From')
    message = data.get('Body', '')
    
    # Get user data from database
    user_data = supabase_client.get_user_by_phone(phone)
    
    # Process message through conversation manager
    result = await conversation_manager.process_message(phone, message, user_data)
    
    # Handle background tasks based on state
    if result['intent'] == 'request_plan':
        background_tasks.add_task(
            run_full_meal_plan_flow, 
            phone,
            conversation_store
        )
    elif result['intent'] == 'confirm':
        background_tasks.add_task(
            generate_and_send_recipes,
            phone,
            conversation_store
        )
    elif result['intent'] in ['swap', 'skip']:
        background_tasks.add_task(
            regenerate_analysis,
            phone,
            conversation_store
        )
    
    # Add help text to response
    response_with_help = format_sms_with_help(
        result['response'],
        result['state']
    )
    
    return create_vonage_response(response_with_help)

# Updated background task to use Redis state
async def run_full_meal_plan_flow(phone: str, store: ConversationStore):
    try:
        # Update status
        store.update_status(phone, ConversationStatus.ANALYZING.value)
        
        # Get state for context
        state = store.get_state(phone)
        
        # Your existing scraper + meal planner logic
        cart_data = await scrape_farm_to_people(credentials)
        preferences = state['context']['user_preferences']
        meal_plan = generate_meal_plan(cart_data, preferences)
        
        # Save analysis to state
        state['context']['last_analysis'] = meal_plan
        state['context']['cart_snapshot'] = cart_data
        state['status'] = ConversationStatus.ANALYSIS_SENT.value
        store.set_state(phone, state)
        
        # Send SMS with analysis
        send_sms(phone, meal_plan)
        
    except Exception as e:
        store.update_status(phone, ConversationStatus.ERROR.value)
        send_sms(phone, "⚠️ Had trouble analyzing your cart. Reply 'plan' to try again.")
```

### **Phase 4: Testing & Migration (30 mins)**

```python
# Test script for Redis state management
async def test_conversation_flow():
    store = ConversationStore()
    manager = ConversationManager(store)
    
    # Test 1: New conversation
    result = await manager.process_message("+1234567890", "plan")
    assert result['state'] == ConversationStatus.ANALYZING.value
    
    # Test 2: State persistence
    state = store.get_state("+1234567890")
    assert state is not None
    assert state['status'] == ConversationStatus.ANALYZING.value
    
    # Test 3: Modification tracking
    store.add_modification("+1234567890", "swap", {"old": "salmon", "new": "chicken"})
    state = store.get_state("+1234567890")
    assert len(state['context']['modifications']) == 1
    
    print("✅ All tests passed!")
```

---

## 🚀 Deployment Configuration

### **Local Development**
```bash
# Install Redis locally
brew install redis
brew services start redis

# Or use Docker
docker run -d -p 6379:6379 redis:alpine
```

### **Environment Variables**
```bash
# .env file
REDIS_URL=redis://localhost:6379  # Local
# or
REDIS_URL=redis://:password@redis-server.railway.internal:6379  # Production
```

### **Railway Deployment**
```yaml
# railway.toml
[services.redis]
source = "redis"
version = "7"
```

---

## 📊 Benefits Over Simple Dictionary

| Feature | Simple Dict | Redis + Structure |
|---------|------------|------------------|
| Survives restart | ❌ | ✅ |
| Multiple servers | ❌ | ✅ |
| Conversation history | ❌ | ✅ |
| Auto-expiry | ❌ | ✅ |
| Debugging tools | Limited | Rich |
| Performance | Fast | Fast |
| Complexity | Low | Medium |

---

## 🔄 Migration Path

### **From Simple Dict → Redis**
```python
# Easy migration - same interface
# OLD:
conversation_states[phone] = {"status": "analyzing"}

# NEW:
conversation_store.update_status(phone, "analyzing")
```

### **Future: Redis → Full State Machine**
- Redis structure stays the same
- Just add state transition validation
- No data migration needed

---

## 🎯 Wednesday Timeline

| Time | Task | Duration |
|------|------|----------|
| 9:00 AM | Redis setup & testing | 30 mins |
| 9:30 AM | ConversationStore implementation | 45 mins |
| 10:15 AM | ConversationManager build | 1.5 hours |
| 11:45 AM | Break | 15 mins |
| 12:00 PM | Server integration | 1.5 hours |
| 1:30 PM | Testing & debugging | 30 mins |
| 2:00 PM | Done! | ✅ |

---

## 🚨 Common Pitfalls & Solutions

1. **Redis Connection Issues**
   - Solution: Fallback to in-memory if Redis down
   
2. **State Synchronization**
   - Solution: Always read-modify-write in single operation
   
3. **TTL Expiry During Conversation**
   - Solution: Refresh TTL on every interaction

4. **Large State Objects**
   - Solution: Store analysis separately with reference

---

*This implementation provides robust, scalable conversation state management while maintaining simplicity and clear upgrade paths.*