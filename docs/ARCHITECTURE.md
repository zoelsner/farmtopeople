# 🏗️ Farm to People Architecture Documentation

## System Overview

Farm to People AI Assistant is a modular web application that transforms weekly produce boxes into personalized meal plans. The system uses a service-oriented architecture on the backend and a modular JavaScript architecture on the frontend.

**Last Updated:** September 4, 2025  
**Version:** 5.0.0

## Architecture Principles

1. **Separation of Concerns**: Each module handles a specific domain
2. **Event-Driven Communication**: Modules communicate via event bus, not direct coupling
3. **Data Isolation**: Complete user data isolation to prevent cross-contamination
4. **Cache-First Strategy**: Redis caching with 1-hour TTL reduces API load
5. **Security by Design**: Fernet encryption, phone normalization, ownership verification

## System Components

### Frontend Architecture

```
dashboard_refactored.html (750 lines)
    ├── HTML Structure
    ├── CSS Styles
    └── Module Initialization
    
/static/js/modules/
    ├── shared.js (140 lines)
    │   ├── Global State Management (AppState)
    │   ├── Event Bus
    │   ├── API Utilities
    │   └── Common Helpers
    │
    ├── cart-manager.js (450 lines)
    │   ├── Cart Analysis
    │   ├── Scraping Orchestration
    │   ├── Category Counting
    │   └── Meal Suggestions
    │
    ├── meal-planner.js (650 lines)
    │   ├── Weekly Calendar
    │   ├── Drag & Drop
    │   ├── Ingredient Pool Tracking
    │   └── Meal Generation
    │
    └── settings.js (430 lines)
        ├── User Preferences
        ├── Modal Management
        └── Database Sync
```

### Backend Services Architecture

```
server.py (1647 lines, down from 2000+)
    ├── FastAPI Application
    ├── Route Handlers
    └── Service Delegation
    
/services/
    ├── phone_service.py
    │   └── normalize_phone() → E.164 format
    │
    ├── sms_handler.py
    │   └── route_sms_message() → (response, should_trigger_task)
    │
    ├── account_service.py
    │   └── lookup_user_account() → user_data with isolation
    │
    ├── scraper_service.py
    │   └── scrape_user_cart() → cart_data with caching
    │
    ├── meal_generator.py
    │   └── generate_meals_from_cart() → meal suggestions
    │
    ├── cart_service.py
    │   └── analyze_cart() → analysis with force_refresh
    │
    ├── cache_service.py
    │   ├── get_cart() → cached data
    │   └── set_cart() → 1hr TTL
    │
    ├── encryption_service.py
    │   ├── encrypt_password() → Fernet encrypted
    │   └── decrypt_password() → Plain text
    │
    ├── data_isolation_service.py
    │   ├── create_isolated_context()
    │   └── verify_cart_ownership()
    │
    └── meal_flow_service.py
        └── run_full_meal_plan_flow() → Complete orchestration
```

## Data Flow

### 1. Cart Analysis Flow
```
User clicks "Analyze Cart"
    ↓
cart-manager.js → POST /api/analyze-cart
    ↓
server.py → cart_service.py
    ↓
Check Redis cache (1hr TTL)
    ↓ (cache miss)
scraper_service.py → Farm to People
    ↓
Store in Redis & Supabase
    ↓
Return cart_data
    ↓
eventBus.emit('cart-analyzed', cartData)
    ↓
meal-planner.js receives event → Initialize meal plan
```

### 2. Ingredient Allocation Flow
```
Cart Data Received
    ↓
Build Ingredient Pool
    {
        "Chicken Breast": {
            total: 4,
            allocated: 0,
            remaining: 4,
            unit: "lbs"
        }
    }
    ↓
Generate Meal for Monday
    ↓
Allocate 1lb Chicken to Monday
    {
        allocated: 1,
        remaining: 3
    }
    ↓
Update Progress Bar (25% used)
    ↓
Drag Monday meal to Tuesday
    ↓
Move allocation with meal
```

### 3. Cross-Module Communication
```javascript
// Cart module completes analysis
cartManager.analyze() 
    → eventBus.emit('cart-analyzed', cartData)

// Meal module receives data
mealPlanner.on('cart-analyzed', (cartData) => {
    this.initializeMealPlan(cartData);
});

// Settings module updates preferences
settingsManager.save()
    → eventBus.emit('preferences-updated', prefs)

// Meal module regenerates with new preferences
mealPlanner.on('preferences-updated', (prefs) => {
    this.regenerateWithPreferences(prefs);
});
```

## Security Architecture

### Phone Normalization (Prevents Data Bleeding)
```python
# All phone formats resolve to same E.164
normalize_phone("2125551234")     → "+12125551234"
normalize_phone("(212) 555-1234") → "+12125551234"
normalize_phone("+12125551234")   → "+12125551234"
```

### Data Isolation Pattern
```python
# Every request creates isolated context
context = UserDataIsolation.create_isolated_context(phone)
# Unique session key per user
session_key = hashlib.sha256(f"{phone}{timestamp}".encode()).hexdigest()

# Verify ownership before returning data
if not verify_cart_ownership(requested_phone, cart_data):
    return {}  # Block contaminated data
```

### Password Encryption Migration
```python
# Old: Base64 (insecure)
encoded = base64.b64encode(password.encode()).decode()

# New: Fernet (symmetric encryption)
cipher = Fernet(encryption_key)
encrypted = cipher.encrypt(password.encode())
```

## Caching Strategy

### Redis Configuration
- **TTL**: 1 hour for cart data
- **Force Refresh**: User can bypass cache
- **Graceful Fallback**: Works without Redis

```python
class CacheService:
    @staticmethod
    def get_cart(phone: str):
        if not redis_client:
            return None  # Graceful degradation
        
        cached = redis_client.get(f"cart:{phone}")
        if cached and not expired:
            return json.loads(cached)
        return None
    
    @staticmethod
    def set_cart(phone: str, data: dict, ttl: int = 3600):
        if redis_client:
            redis_client.setex(
                f"cart:{phone}",
                ttl,
                json.dumps(data)
            )
```

## State Management

### Global State Object
```javascript
window.AppState = {
    currentState: 'initial',  // initial|loading|complete|error
    mealPlanData: null,        // Cart and meal data
    userSettings: null,        // User preferences
    phoneNumber: null          // Cached phone
};
```

### Local Storage Strategy
- Cart analysis: 1-hour cache
- Meal plans: Per-week storage
- User settings: Persistent
- Credentials: Never stored in JS

## API Endpoints

### Cart Management
- `POST /api/analyze-cart`
  - Body: `{ phone_number, force_refresh }`
  - Returns: `{ success, cart_data }`

### Meal Planning
- `POST /api/generate-weekly-meals`
  - Body: `{ phone_number, ingredient_pool, preferences }`
  - Returns: `{ meals: [...] }`

- `POST /api/regenerate-meal`
  - Body: `{ phone_number, day, available_ingredients }`
  - Returns: `{ meal }`

- `POST /api/generate-recipe`
  - Body: `{ phone_number, meal, ingredients }`
  - Returns: `{ recipe_url }`

### User Management
- `GET /api/user-settings?phone={phone}`
  - Returns: `{ success, user_data }`

- `POST /api/update-preferences`
  - Body: `{ phone_number, preferences }`
  - Returns: `{ success }`

## Performance Optimizations

1. **Code Splitting**: 2954 lines → 5 files averaging 400 lines
2. **Lazy Loading**: Modules load only when tab activated
3. **Event Debouncing**: Prevents rapid API calls
4. **Cache-First**: Reduces Farm to People server load
5. **Batch Operations**: Multiple tool calls in parallel

## Deployment Architecture

### Railway Configuration
- **Auto-deploy**: From GitHub main branch
- **Python**: 3.8 (compatibility requirement)
- **Redis**: Add-on service for caching
- **Environment Variables**: Stored in Railway

### Static File Serving
```python
app.mount("/static", StaticFiles(directory="server/static"), name="static")
```

## Monitoring & Debugging

### Key Metrics
- Cart analysis time: Target <30 seconds
- Cache hit rate: Target >70%
- Phone normalization success: >99%
- Data isolation verification: 100%

### Debug Points
```javascript
// Frontend debugging
console.log('Cart analyzed:', cartData);
console.log('Event emitted:', eventName, data);
console.log('State updated:', window.AppState);

// Backend debugging
print(f"📞 Phone normalized: {original} → {normalized}")
print(f"🔍 Cache {'hit' if cached else 'miss'} for {phone}")
print(f"✅ Data ownership verified for {phone}")
```

## Future Improvements

1. **WebSocket Communication**: Real-time updates during scraping
2. **Service Workers**: Offline meal planning
3. **GraphQL API**: More efficient data fetching
4. **React Migration**: When team scales beyond 1
5. **Kubernetes**: When scaling beyond Railway

## Migration Guide

### From Monolithic to Modular
1. Backup original: `cp dashboard.html dashboard_backup.html`
2. Deploy modules: Ensure `/static/js/modules/` accessible
3. Update imports: Switch to dashboard_refactored.html
4. Test locally: All features working
5. Deploy: Git push triggers Railway

### Rollback Procedure
```bash
# If issues arise
cp dashboard_backup.html dashboard.html
git commit -m "Rollback to monolithic dashboard"
git push
```

---

*This architecture supports the current scale while remaining simple enough for a single developer to maintain. The modular design allows for incremental improvements without system-wide refactoring.*