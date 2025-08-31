# 🍽️ **WEEKLY MEAL CALENDAR IMPLEMENTATION PLAN**
*Detailed implementation plan for drag-and-drop meal planning with ingredient allocation*

**Created:** August 31, 2025  
**Status:** In Development  
**Architecture:** Supabase + localStorage hybrid (Redis-ready)

---

## 📊 **SYSTEM OVERVIEW**

### **Core Concept:**
Transform weekly produce box contents into an interactive meal calendar where users can:
- View 5-day meal plan (Monday-Friday)
- Drag meals between days
- Regenerate individual meals with smart ingredient consideration
- Track ingredient allocation across the week

### **Key Innovation:**
**Smart Ingredient Allocation** - When meals are moved/regenerated, the system tracks ingredient usage to prevent over-allocation and suggests realistic portions based on actual cart contents.

---

## 🏗️ **DATABASE ARCHITECTURE**

### **Tables Created:**
```sql
weekly_meal_plans      -- Main meal plan container
meal_assignments       -- Individual meals per day
ingredient_pools       -- Ingredient availability tracking
meal_plan_sessions     -- Cross-device sync sessions
```

### **Key Features:**
- **Automatic ingredient pool initialization** from cart data
- **Conflict detection** for ingredient over-allocation
- **Transaction-safe** meal assignments with rollback
- **Row-level security** for multi-user support
- **Real-time sync** capability via Supabase subscriptions

---

## 🎯 **IMPLEMENTATION PHASES**

### **Phase 1: Backend Foundation (3-4 days)**
- [x] **Day 1:** Database schema creation
- [x] **Day 2:** Storage abstraction layer
- [x] **Day 3:** Supabase storage implementation
- [ ] **Day 4:** API endpoints and session management

### **Phase 2: Meal Generation Logic (2-3 days)**
- [ ] **Day 5:** Context-aware AI meal generation
- [ ] **Day 6:** Smart ingredient allocation algorithms

### **Phase 3: Frontend Implementation (4-5 days)**
- [ ] **Day 7-8:** Weekly calendar component with drag & drop
- [ ] **Day 9-10:** Real-time sync and regeneration flows
- [ ] **Day 11:** Mobile optimization and polish

---

## 🔧 **TECHNICAL SPECIFICATIONS**

### **Storage Architecture (Redis-Ready):**
```python
# Abstract base class allows easy migration to Redis
class MealPlanStorage(ABC):
    async def create_meal_plan(self, user_phone: str, week_of: date, cart_data: Dict) -> str
    async def assign_meal(self, plan_id: str, day: str, meal_data: Dict, ingredients: List[Dict]) -> bool
    async def get_ingredient_pool(self, plan_id: str) -> Dict[str, Dict]
    # ... etc

# Current: SupabaseMealStorage 
# Future: RedisMealStorage (drop-in replacement)
storage = SupabaseMealStorage()
```

### **Ingredient Allocation Logic:**
```python
def allocate_ingredients(plan_id: str, meal_day: str, ingredients: List[Dict]):
    """
    Smart allocation with conflict prevention:
    1. Load current ingredient pool
    2. Check availability vs requested amounts
    3. Detect conflicts and suggest alternatives
    4. Atomically allocate if no conflicts
    5. Return success or detailed conflict info
    """
```

### **Smart Regeneration Strategy:**
```python
async def regenerate_meal(plan_id: str, day: str):
    """
    Context-aware meal regeneration:
    1. Release current meal's ingredients back to pool
    2. Get updated available ingredients
    3. Consider other meals this week (avoid duplication)
    4. Generate meal with AI using available ingredients only
    5. Validate and allocate new ingredients
    """
```

---

## 📱 **FRONTEND STATE MANAGEMENT**

### **State Structure:**
```javascript
const mealPlanState = {
  planId: "uuid-here",
  weekOf: "2025-08-31", 
  meals: {
    monday: {meal_data, allocated_ingredients, status},
    tuesday: null, // empty day
    // ...
  },
  availableIngredients: {
    "Chicken Breast": {total: 1.0, allocated: 0.5, remaining: 0.5}
  },
  uiState: {dragInProgress: false, regeneratingDays: []}
}
```

### **Real-time Sync Strategy:**
- **Optimistic Updates:** Show changes immediately
- **Background Sync:** Push to Supabase within 300ms
- **Conflict Resolution:** Last-write-wins with user notification
- **Cross-device:** Supabase realtime subscriptions

---

## ⚡ **PERFORMANCE OPTIMIZATIONS**

### **Database:**
- Indexed on `(user_phone, week_of)` for fast lookups
- JSONB GIN indexes for ingredient searching  
- Connection pooling for concurrency
- Partial indexes on active sessions only

### **Frontend:**
- Debounced sync (300ms) for rapid changes
- localStorage cache for offline capability
- Virtualized components for scale
- Service worker for background sync

---

## 🚀 **MIGRATION PATH TO REDIS**

**When to migrate:** >100 active users, need <100ms sync

**Phase 1:** Redis as cache layer
- Keep Supabase as source of truth
- Redis for active meal planning sessions (10min TTL)
- WebSocket connections for instant updates

**Code changes needed:** Just swap storage implementation
```python
storage = RedisMealStorage() if USE_REDIS else SupabaseMealStorage()
```

---

## 📊 **SUCCESS METRICS**

### **Technical:**
- Meal generation: <3 seconds
- Cross-device sync: <500ms  
- Ingredient accuracy: >95%
- Zero data loss during conflicts

### **User Experience:**
- Plan completion rate: >80%
- Time to weekly plan: <5 minutes
- Generated meal satisfaction: >4/5 stars
- Cross-device adoption: >30%

---

## 🎯 **USER FLOW EXAMPLE**

1. **Cart Analysis** → Generate initial 5-day meal plan
2. **Review Calendar** → See Monday-Friday with meals assigned
3. **Drag Meal** → Move Tuesday's meal to Wednesday
   - System automatically checks ingredient availability
   - Shows conflict if Wednesday+Tuesday meals exceed ingredients
   - Suggests portion adjustments or alternatives
4. **Regenerate Meal** → Click refresh on Thursday
   - AI considers remaining ingredients after Mon-Wed allocations
   - Generates new meal avoiding duplication
   - Updates ingredient pool automatically
5. **Lock Plan** → Finalize and generate shopping list for missing ingredients

---

## 🔄 **NEXT ACTIONS**

1. **Immediate:** Run Supabase schema setup
2. **This week:** Complete API endpoints and basic frontend
3. **Next week:** Add drag & drop and real-time sync
4. **Future:** Redis migration and advanced features

---

*This plan balances innovation (smart ingredient allocation) with practical implementation (modular architecture). The drag & drop meal calendar with real ingredient constraints is the key differentiator that makes this more than just another recipe app.*