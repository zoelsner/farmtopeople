# 🔧 Farm to People Refactoring & Efficiency Opportunities
*System optimization analysis for tomorrow's work*

## 🎯 HIGH-PRIORITY REFACTORING

### 1. **Advanced Conversation State Management** 🧠
**Current Issue:** No persistent conversation context across messages
**Impact:** Can't handle complex multi-turn conversations, modifications, or interruptions

### 🏗️ **ARCHITECTURE OPTIONS FOR CONVERSATION STATE**

#### **Option A: Finite State Machine (FSM) Pattern**
```python
# server/conversation/state_machine.py
from enum import Enum
from typing import Dict, Optional, List
import json
from datetime import datetime, timedelta

class ConversationState(Enum):
    # Linear flow states
    IDLE = "idle"
    ANALYZING_CART = "analyzing_cart"
    ANALYSIS_SENT = "analysis_sent"
    MODIFYING_PLAN = "modifying_plan"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    CONFIRMED = "confirmed"
    RECIPES_SCHEDULED = "recipes_scheduled"
    
    # Error/special states
    ERROR_RECOVERY = "error_recovery"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class StateTransition:
    def __init__(self, from_state: ConversationState, 
                 trigger: str, 
                 to_state: ConversationState,
                 condition: Optional[callable] = None,
                 action: Optional[callable] = None):
        self.from_state = from_state
        self.trigger = trigger
        self.to_state = to_state
        self.condition = condition
        self.action = action

class ConversationFSM:
    def __init__(self, phone: str):
        self.phone = phone
        self.state = ConversationState.IDLE
        self.context = {
            "created_at": datetime.now(),
            "modifications": [],
            "cart_snapshot": None,
            "analysis": None,
            "confirmed_order": None
        }
        self.transitions = self._define_transitions()
        self.state_history = []
    
    def _define_transitions(self) -> List[StateTransition]:
        return [
            # Happy path
            StateTransition(ConversationState.IDLE, "plan", 
                          ConversationState.ANALYZING_CART,
                          action=self.start_analysis),
            
            StateTransition(ConversationState.ANALYZING_CART, "analysis_complete", 
                          ConversationState.ANALYSIS_SENT,
                          action=self.send_analysis),
            
            StateTransition(ConversationState.ANALYSIS_SENT, "confirm", 
                          ConversationState.CONFIRMED,
                          action=self.confirm_order),
            
            # Modification paths
            StateTransition(ConversationState.ANALYSIS_SENT, "swap|remove|skip", 
                          ConversationState.MODIFYING_PLAN,
                          action=self.start_modification),
            
            StateTransition(ConversationState.MODIFYING_PLAN, "modification_complete", 
                          ConversationState.ANALYSIS_SENT,
                          action=self.send_updated_analysis),
            
            # Recovery paths
            StateTransition(ConversationState.ERROR_RECOVERY, "retry", 
                          ConversationState.IDLE),
            
            # Allow restart from any state
            StateTransition(None, "start_over", 
                          ConversationState.IDLE,
                          action=self.reset_context),
        ]
    
    def process_message(self, message: str) -> Dict:
        """Process incoming message and transition states"""
        self.state_history.append({
            "state": self.state,
            "message": message,
            "timestamp": datetime.now()
        })
        
        # Find valid transitions from current state
        valid_transitions = [
            t for t in self.transitions 
            if t.from_state in (self.state, None) and 
               self._matches_trigger(message, t.trigger)
        ]
        
        for transition in valid_transitions:
            if transition.condition and not transition.condition(self.context):
                continue
                
            # Execute transition
            self.state = transition.to_state
            if transition.action:
                result = transition.action(message, self.context)
                return result
        
        # No valid transition found
        return self.handle_invalid_input(message)
```

**Pros:** Clear state flow, easy to visualize, prevents invalid transitions
**Cons:** Can be rigid for complex conversations, harder to handle interruptions

---

#### **Option B: Event Sourcing with Context Accumulation**
```python
# server/conversation/event_sourcing.py
from dataclasses import dataclass
from typing import List, Dict, Any
import uuid
from datetime import datetime

@dataclass
class ConversationEvent:
    event_id: str
    phone: str
    event_type: str
    payload: Dict[str, Any]
    timestamp: datetime
    
class ConversationEventStore:
    """Store all events for perfect replay and debugging"""
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.ttl = 7200  # 2 hours
    
    def append_event(self, phone: str, event_type: str, payload: Dict):
        event = ConversationEvent(
            event_id=str(uuid.uuid4()),
            phone=phone,
            event_type=event_type,
            payload=payload,
            timestamp=datetime.now()
        )
        
        # Store in Redis list
        key = f"events:{phone}"
        self.redis.rpush(key, json.dumps(dataclasses.asdict(event)))
        self.redis.expire(key, self.ttl)
        
        return event
    
    def get_conversation_context(self, phone: str) -> Dict:
        """Rebuild context by replaying all events"""
        events = self.get_events(phone)
        context = self._build_context_from_events(events)
        return context
    
    def _build_context_from_events(self, events: List[ConversationEvent]) -> Dict:
        context = {
            "state": "idle",
            "cart": None,
            "analysis": None,
            "modifications": [],
            "confirmations": [],
            "errors": []
        }
        
        for event in events:
            if event.event_type == "cart_analyzed":
                context["cart"] = event.payload["cart"]
                context["state"] = "analysis_sent"
            
            elif event.event_type == "modification_requested":
                context["modifications"].append(event.payload)
                context["state"] = "modifying"
            
            elif event.event_type == "order_confirmed":
                context["confirmations"].append(event.payload)
                context["state"] = "confirmed"
            
            elif event.event_type == "error_occurred":
                context["errors"].append(event.payload)
                # Don't change state on error
        
        return context

class EventBasedConversationManager:
    def __init__(self, event_store: ConversationEventStore):
        self.event_store = event_store
        self.handlers = self._init_handlers()
    
    async def process_message(self, phone: str, message: str) -> str:
        # Get current context by replaying events
        context = self.event_store.get_conversation_context(phone)
        
        # Classify intent regardless of state
        intent = self.classify_intent(message, context)
        
        # Record incoming message event
        self.event_store.append_event(
            phone, 
            "message_received",
            {"message": message, "intent": intent}
        )
        
        # Route to appropriate handler based on intent AND context
        handler = self.select_handler(intent, context)
        response = await handler(phone, message, context)
        
        # Record response event
        self.event_store.append_event(
            phone,
            "response_sent", 
            {"response": response}
        )
        
        return response
```

**Pros:** Complete audit trail, can replay conversations, flexible state transitions
**Cons:** More complex, requires more storage, rebuilding context can be slow

---

#### **Option C: Graph-Based Conversation Flow**
```python
# server/conversation/graph_flow.py
import networkx as nx
from typing import Dict, List, Optional

class ConversationGraph:
    """Non-linear conversation flow using directed graph"""
    
    def __init__(self):
        self.graph = nx.DiGraph()
        self._build_conversation_graph()
        self.user_positions = {}  # phone -> current_node
        
    def _build_conversation_graph(self):
        # Define nodes (conversation states)
        nodes = [
            ("start", {"type": "entry", "message": "Welcome!"}),
            ("analyzing", {"type": "processing", "timeout": 30}),
            ("analysis_ready", {"type": "decision", "options": ["confirm", "modify", "cancel"]}),
            ("modifying", {"type": "interactive", "allows": ["swap", "remove", "skip"]}),
            ("confirming", {"type": "checkpoint"}),
            ("complete", {"type": "terminal"}),
            ("error", {"type": "recovery"})
        ]
        
        # Add nodes with attributes
        for node_id, attrs in nodes:
            self.graph.add_node(node_id, **attrs)
        
        # Define edges (valid transitions) with conditions
        edges = [
            ("start", "analyzing", {"trigger": "plan", "weight": 1.0}),
            ("analyzing", "analysis_ready", {"trigger": "auto", "weight": 1.0}),
            ("analysis_ready", "confirming", {"trigger": "confirm", "weight": 0.8}),
            ("analysis_ready", "modifying", {"trigger": "change", "weight": 0.2}),
            ("modifying", "analysis_ready", {"trigger": "done", "weight": 1.0}),
            ("confirming", "complete", {"trigger": "auto", "weight": 1.0}),
            
            # Allow jumping back from any state
            ("modifying", "start", {"trigger": "restart", "weight": 0.1}),
            ("confirming", "modifying", {"trigger": "wait", "weight": 0.1}),
            
            # Error handling edges
            ("analyzing", "error", {"trigger": "timeout", "weight": 0.1}),
            ("error", "start", {"trigger": "retry", "weight": 1.0})
        ]
        
        self.graph.add_edges_from(edges)
    
    def navigate(self, phone: str, message: str) -> Dict:
        """Navigate through conversation graph based on message"""
        current_node = self.user_positions.get(phone, "start")
        
        # Get possible next nodes
        possible_moves = list(self.graph.successors(current_node))
        
        # Score each possible move based on message match
        best_move = self.select_best_move(
            current_node, 
            possible_moves, 
            message
        )
        
        if best_move:
            self.user_positions[phone] = best_move
            return self.execute_node_action(best_move, message)
        else:
            # No valid move - stay in current node
            return self.handle_invalid_move(current_node, message)
    
    def select_best_move(self, current: str, possible: List[str], message: str) -> Optional[str]:
        """Use edge weights and triggers to select best next node"""
        scores = {}
        
        for next_node in possible:
            edge_data = self.graph.edges[current, next_node]
            trigger = edge_data.get("trigger", "")
            weight = edge_data.get("weight", 0.5)
            
            # Score based on trigger match
            if trigger == "auto":
                scores[next_node] = weight
            elif trigger in message.lower():
                scores[next_node] = weight * 2  # Boost for keyword match
            elif self.fuzzy_match(trigger, message):
                scores[next_node] = weight * 1.5
        
        return max(scores, key=scores.get) if scores else None
```

**Pros:** Flexible non-linear flows, can handle interruptions, visual representation
**Cons:** More complex to implement, harder to debug

---

#### **Option D: Hybrid Context Manager (RECOMMENDED)**
```python
# server/conversation/hybrid_manager.py
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import pickle
import redis

@dataclass
class ConversationContext:
    """Rich context object that accumulates information"""
    phone: str
    state: str = "idle"
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    
    # Core data
    cart_data: Optional[Dict] = None
    user_preferences: Optional[Dict] = None
    current_analysis: Optional[str] = None
    
    # Modification tracking
    modifications: List[Dict] = field(default_factory=list)
    skipped_days: List[str] = field(default_factory=list)
    swapped_items: Dict[str, str] = field(default_factory=dict)
    
    # State flags
    is_confirmed: bool = False
    recipes_sent: bool = False
    awaiting_response: bool = False
    last_question_asked: Optional[str] = None
    
    # Error recovery
    error_count: int = 0
    last_error: Optional[str] = None
    
    def is_expired(self) -> bool:
        return datetime.now() - self.last_activity > timedelta(hours=2)
    
    def add_modification(self, mod_type: str, details: Dict):
        self.modifications.append({
            "type": mod_type,
            "details": details,
            "timestamp": datetime.now()
        })
        self.last_activity = datetime.now()
    
    def can_transition_to(self, new_state: str) -> bool:
        """Validate state transitions"""
        valid_transitions = {
            "idle": ["analyzing"],
            "analyzing": ["analysis_sent", "error"],
            "analysis_sent": ["modifying", "confirmed", "idle"],
            "modifying": ["analysis_sent", "confirmed"],
            "confirmed": ["recipes_sent", "modifying"],
            "recipes_sent": ["idle"]
        }
        return new_state in valid_transitions.get(self.state, [])

class HybridConversationManager:
    """Combines state machine, event tracking, and rich context"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.ttl = 7200  # 2 hour TTL
        
    def get_or_create_context(self, phone: str) -> ConversationContext:
        """Retrieve existing context or create new one"""
        key = f"context:{phone}"
        
        # Try to get existing context
        stored = self.redis.get(key)
        if stored:
            context = pickle.loads(stored)
            if not context.is_expired():
                return context
        
        # Create new context
        context = ConversationContext(phone=phone)
        self.save_context(context)
        return context
    
    def save_context(self, context: ConversationContext):
        """Persist context to Redis"""
        key = f"context:{context.phone}"
        self.redis.setex(
            key,
            self.ttl,
            pickle.dumps(context)
        )
    
    async def process_message(self, phone: str, message: str) -> str:
        """Main entry point for processing messages"""
        context = self.get_or_create_context(phone)
        
        # Handle expired context
        if context.is_expired():
            context = ConversationContext(phone=phone)
            return await self.handle_new_conversation(context, message)
        
        # Route based on current state and message intent
        intent = self.classify_intent(message, context)
        
        # Special handlers for any state
        if intent == "help":
            return self.send_help(context)
        elif intent == "start_over":
            context = ConversationContext(phone=phone)
            return await self.handle_new_conversation(context, message)
        
        # State-specific routing
        handler_map = {
            "idle": self.handle_idle_state,
            "analyzing": self.handle_analyzing_state,
            "analysis_sent": self.handle_analysis_sent_state,
            "modifying": self.handle_modifying_state,
            "confirmed": self.handle_confirmed_state,
            "recipes_sent": self.handle_recipes_sent_state
        }
        
        handler = handler_map.get(context.state, self.handle_unknown_state)
        response = await handler(context, message, intent)
        
        # Update context
        context.last_activity = datetime.now()
        self.save_context(context)
        
        # Log for debugging
        self.log_interaction(context, message, intent, response)
        
        return response
    
    def classify_intent(self, message: str, context: ConversationContext) -> str:
        """Smart intent classification based on message AND context"""
        message_lower = message.lower()
        
        # Context-aware intent detection
        if context.awaiting_response and context.last_question_asked:
            # User is responding to a specific question
            if "yes" in message_lower or "👍" in message:
                return "affirmative"
            elif "no" in message_lower or "👎" in message:
                return "negative"
        
        # Keyword-based intents
        intent_keywords = {
            "plan": ["plan", "meal", "help me", "what can i make"],
            "confirm": ["confirm", "yes", "looks good", "perfect"],
            "swap": ["swap", "replace", "instead of", "change"],
            "remove": ["remove", "delete", "don't want", "no"],
            "skip": ["skip", "not cooking", "away", "out"],
            "help": ["help", "what", "how", "confused"],
            "start_over": ["start over", "restart", "cancel", "nevermind"],
            "recipes_now": ["recipes now", "send recipes", "instructions"]
        }
        
        for intent, keywords in intent_keywords.items():
            if any(kw in message_lower for kw in keywords):
                return intent
        
        return "unknown"
    
    async def handle_analysis_sent_state(self, context: ConversationContext, 
                                        message: str, intent: str) -> str:
        """Handle messages when analysis has been sent"""
        
        if intent == "confirm":
            if context.can_transition_to("confirmed"):
                context.state = "confirmed"
                context.is_confirmed = True
                return await self.send_confirmation(context)
        
        elif intent == "swap":
            context.state = "modifying"
            swap_details = self.parse_swap_request(message)
            context.add_modification("swap", swap_details)
            return await self.process_swap(context, swap_details)
        
        elif intent == "remove":
            context.state = "modifying"
            remove_details = self.parse_remove_request(message)
            context.add_modification("remove", remove_details)
            return await self.process_removal(context, remove_details)
        
        elif intent == "skip":
            context.state = "modifying"
            skip_days = self.parse_skip_days(message)
            context.skipped_days.extend(skip_days)
            context.add_modification("skip", {"days": skip_days})
            return await self.regenerate_analysis(context)
        
        else:
            # Ask for clarification
            context.awaiting_response = True
            context.last_question_asked = "confirm_or_modify"
            return ("I see you reviewed the meal plan. Would you like to:\n"
                   "- CONFIRM to proceed\n"
                   "- SWAP items\n"
                   "- SKIP certain days\n"
                   "- START OVER")
    
    def log_interaction(self, context: ConversationContext, 
                        message: str, intent: str, response: str):
        """Log for debugging and analytics"""
        log_entry = {
            "phone": context.phone,
            "state": context.state,
            "message": message,
            "intent": intent,
            "response_preview": response[:100],
            "timestamp": datetime.now().isoformat(),
            "modifications_count": len(context.modifications),
            "error_count": context.error_count
        }
        
        # Store in Redis list for debugging
        self.redis.lpush(f"logs:{context.phone}", json.dumps(log_entry))
        self.redis.ltrim(f"logs:{context.phone}", 0, 99)  # Keep last 100
```

**Pros:** 
- Balances structure with flexibility
- Rich context tracking
- Easy to debug with logs
- Handles interruptions gracefully
- Supports both linear and non-linear flows

**Cons:**
- More code to maintain
- Requires Redis for persistence

---

### **CONVERSATION STATE EDGE CASES TO HANDLE**

```python
class EdgeCaseHandlers:
    """Handle tricky conversation scenarios"""
    
    def handle_duplicate_request(self, context: ConversationContext) -> str:
        """User sends 'plan' while analysis is running"""
        if context.state == "analyzing":
            time_elapsed = datetime.now() - context.last_activity
            if time_elapsed < timedelta(seconds=30):
                return "Still working on your analysis! Results coming in a moment..."
            else:
                # Might be stuck - restart
                return "Let me restart that analysis for you..."
    
    def handle_context_switch(self, context: ConversationContext, 
                              new_topic: str) -> str:
        """User suddenly asks about something else"""
        if new_topic == "pricing":
            # Save current context but respond to new query
            context.add_modification("interrupted", {"reason": "pricing_query"})
            return "Farm to People boxes start at $35. Want to continue with your meal plan?"
    
    def handle_family_sharing(self, phone: str, message: str) -> ConversationContext:
        """Multiple family members might text from same number"""
        # Look for name indicators
        if message.startswith("This is"):
            name = self.extract_name(message)
            return self.get_or_create_context(f"{phone}:{name}")
        return self.get_or_create_context(phone)
    
    def handle_delayed_response(self, context: ConversationContext) -> str:
        """User responds hours/days later"""
        time_gap = datetime.now() - context.last_activity
        
        if time_gap > timedelta(hours=24):
            return (f"Welcome back! You were working on a meal plan {time_gap.days} days ago. "
                   "Reply 'continue' to pick up where you left off, or 'new' to start fresh.")
        elif time_gap > timedelta(hours=2):
            # Remind them where they were
            return f"Welcome back! You were {context.state}. Ready to continue?"
    
    def handle_correction(self, context: ConversationContext, message: str) -> str:
        """User wants to correct previous input"""
        if "actually" in message or "wait" in message or "oops" in message:
            # Roll back last modification
            if context.modifications:
                last_mod = context.modifications.pop()
                return f"No problem! I've undone the {last_mod['type']}. What would you like instead?"
```

---

### 2. **Scraper Performance Optimization** 🚀
**Current Issue:** Takes 30-45 seconds per scrape
**Impact:** Poor user experience waiting for analysis

**Proposed Solutions:**
```python
# 1. Parallel box processing
async def scrape_boxes_parallel():
    tasks = [
        scrape_individual_items(),
        scrape_customizable_boxes(),
        scrape_non_customizable_boxes()
    ]
    results = await asyncio.gather(*tasks)

# 2. Cache unchanged data
def smart_scrape(user_id):
    last_cart = get_cached_cart(user_id)
    if cart_unchanged_since(last_cart):
        return last_cart
    return full_scrape()

# 3. Headless mode for production
browser = await playwright.chromium.launch(
    headless=True,  # Faster without UI
    args=['--disable-gpu', '--no-sandbox']
)
```

---

### 3. **Modular Message Handlers** 📱
**Current Issue:** Giant if/elif chain in server.py
**Impact:** Hard to maintain, test, and extend

**Proposed Solution:**
```python
# New: server/message_handlers.py
class MessageRouter:
    def __init__(self):
        self.handlers = {
            "plan": PlanHandler(),
            "confirm": ConfirmHandler(),
            "swap": SwapHandler(),
            "skip": SkipHandler(),
            "help": HelpHandler()
        }
    
    async def route(self, phone: str, message: str, context: Dict):
        # Smart routing based on context AND message
        if context["state"] == ConversationState.ANALYSIS_SENT:
            if "swap" in message.lower():
                return await self.handlers["swap"].handle(phone, message, context)
        
        # Default routing
        for keyword, handler in self.handlers.items():
            if keyword in message.lower():
                return await handler.handle(phone, message, context)
        
        return await self.handlers["help"].handle(phone, message, context)
```

---

### 4. **Preference Learning System** 🧠
**Current Issue:** Static preferences from onboarding
**Impact:** Doesn't adapt to user behavior

**Proposed Solution:**
```python
# New: server/preference_evolution.py
class PreferenceEvolution:
    def update_from_feedback(self, user_id: str, feedback: Dict):
        """Evolve preferences based on recipe ratings"""
        prefs = get_user_preferences(user_id)
        
        # Boost successful patterns
        for recipe_id, rating in feedback.items():
            recipe = get_recipe(recipe_id)
            if rating == "👍":
                prefs.boost_signals(recipe.signals, weight=0.1)
            else:
                prefs.reduce_signals(recipe.signals, weight=0.05)
        
        # Detect new patterns
        if all_thumbs_up_are_mediterranean(feedback):
            prefs.add_signal("mediterranean", strength=0.8)
        
        save_evolved_preferences(user_id, prefs)
```

---

## 🔄 ARCHITECTURE IMPROVEMENTS

### 1. **Event-Driven Architecture**
**Current:** Synchronous, blocking operations
**Better:** Event-based with queues

```python
# Using Celery for async tasks
from celery import Celery

app = Celery('farmtopeople')

@app.task
def process_meal_plan_request(phone: str):
    # Long-running tasks in background
    cart = scrape_cart.delay(phone)
    analysis = generate_analysis.delay(cart)
    send_sms.delay(phone, analysis)

# In server.py
if "plan" in message:
    process_meal_plan_request.delay(phone)
    return "Analysis started! Results coming soon..."
```

---

### 2. **Caching Strategy**
**Current:** Scrapes everything every time
**Better:** Smart caching with TTL

```python
from functools import lru_cache
from datetime import datetime, timedelta

class SmartCache:
    def __init__(self):
        self.cache = {}
    
    def get_cart(self, user_id: str, force_refresh=False):
        key = f"cart:{user_id}"
        cached = self.cache.get(key)
        
        # Use cache if fresh (< 2 hours old)
        if cached and not force_refresh:
            age = datetime.now() - cached["timestamp"]
            if age < timedelta(hours=2):
                return cached["data"]
        
        # Otherwise scrape fresh
        fresh_data = scrape_cart(user_id)
        self.cache[key] = {
            "data": fresh_data,
            "timestamp": datetime.now()
        }
        return fresh_data
```

---

### 3. **Error Recovery System**
**Current:** Fails silently or sends generic error
**Better:** Smart retry with fallbacks

```python
class ResilientScraper:
    @retry(max_attempts=3, backoff_factor=2)
    async def scrape_with_retry(self, credentials):
        try:
            return await self.scrape(credentials)
        except AuthenticationError:
            # Try refreshing session
            await self.refresh_session(credentials)
            return await self.scrape(credentials)
        except TimeoutError:
            # Use cached data if available
            cached = self.get_cached_cart(credentials.user_id)
            if cached:
                return cached
            raise
```

---

## 📊 DATABASE OPTIMIZATIONS

### 1. **Indexed Queries**
```sql
-- Add indexes for frequent queries
CREATE INDEX idx_users_phone ON users(phone_number);
CREATE INDEX idx_cart_history_user_date ON cart_history(user_id, scraped_at);
CREATE INDEX idx_feedback_user_recipe ON feedback(user_id, recipe_id);

-- Composite index for preference lookups
CREATE INDEX idx_preferences_user_signals ON preferences(user_id, top_signals);
```

### 2. **Denormalized Views**
```sql
-- Materialized view for fast meal plan generation
CREATE MATERIALIZED VIEW user_meal_context AS
SELECT 
    u.phone_number,
    u.ftp_email,
    p.preferences,
    ch.latest_cart,
    f.recent_feedback
FROM users u
JOIN preferences p ON u.id = p.user_id
LEFT JOIN LATERAL (
    SELECT cart_snapshot as latest_cart 
    FROM cart_history 
    WHERE user_id = u.id 
    ORDER BY scraped_at DESC 
    LIMIT 1
) ch ON true
LEFT JOIN LATERAL (
    SELECT array_agg(feedback) as recent_feedback
    FROM feedback
    WHERE user_id = u.id
    AND feedback_date > NOW() - INTERVAL '30 days'
) f ON true;
```

---

## 🚀 PERFORMANCE IMPROVEMENTS

### 1. **Parallel Processing**
```python
# Current: Sequential
cart = scrape_cart()
prefs = get_preferences()
analysis = generate_analysis(cart, prefs)

# Better: Parallel
async def process_parallel(user_id):
    cart_task = asyncio.create_task(scrape_cart(user_id))
    prefs_task = asyncio.create_task(get_preferences(user_id))
    
    cart, prefs = await asyncio.gather(cart_task, prefs_task)
    return await generate_analysis(cart, prefs)
```

### 2. **Batch Operations**
```python
# Current: Individual SMS sends
for user in users:
    send_sms(user.phone, message)

# Better: Batch API calls
def send_batch_sms(phone_numbers, message):
    vonage_client.send_batch([
        {"to": phone, "text": message}
        for phone in phone_numbers
    ])
```

### 3. **Connection Pooling**
```python
# Database connection pool
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True
)
```

---

## 🧪 TESTING INFRASTRUCTURE

### 1. **Test Data Fixtures**
```python
# tests/fixtures.py
@pytest.fixture
def sample_cart():
    return {
        "individual_items": [...],
        "customizable_boxes": [...],
        "cart_total": "$127.50"
    }

@pytest.fixture
def sample_preferences():
    return {
        "proteins": ["chicken", "salmon"],
        "cuisines": ["mediterranean"],
        "goals": ["high-protein", "quick-dinners"]
    }
```

### 2. **Mock Services**
```python
# tests/mocks.py
class MockScraper:
    async def scrape(self, credentials):
        # Return predictable test data
        return load_fixture("sample_cart.json")

class MockSMS:
    def __init__(self):
        self.sent_messages = []
    
    def send(self, phone, message):
        self.sent_messages.append((phone, message))
        return {"status": "sent"}
```

---

## 📈 MONITORING & OBSERVABILITY

### 1. **Application Metrics**
```python
from prometheus_client import Counter, Histogram, Gauge

# Track key metrics
sms_received = Counter('sms_received_total', 'Total SMS received')
cart_scrape_duration = Histogram('cart_scrape_seconds', 'Cart scraping time')
active_conversations = Gauge('active_conversations', 'Active conversation count')

# Use in code
@sms_received.count_exceptions()
async def handle_sms(phone, message):
    with cart_scrape_duration.time():
        cart = await scrape_cart(phone)
```

### 2. **Structured Logging**
```python
import structlog

logger = structlog.get_logger()

# Rich context logging
logger.info(
    "meal_plan_generated",
    user_id=user_id,
    cart_value=cart_total,
    protein_avg=avg_protein,
    generation_time=elapsed,
    model="gpt-4"
)
```

---

## 🎯 TOMORROW'S PRIORITY ORDER

### **Morning Session (High Impact)**
1. Implement Hybrid Conversation Manager (Option D)
2. Set up Redis for context persistence
3. Build intent classification system

### **Afternoon Session (User Experience)**
1. Create modular message handlers
2. Implement edge case handlers
3. Add conversation state logging

### **Evening Session (Testing)**
1. Set up conversation state tests
2. Test multi-turn conversations
3. Test error recovery flows

---

## 💡 QUICK WINS (< 30 min each)

1. **Add request ID tracking** - Easier debugging
2. **Implement health check endpoint** - Monitor uptime
3. **Create admin SMS commands** - Quick system management
4. **Add rate limiting** - Prevent abuse
5. **Cache FTP credentials** - Reduce DB queries

---

*The Hybrid Conversation Manager (Option D) is recommended as it provides the best balance of structure, flexibility, and debuggability while handling the complex edge cases of SMS conversations.*