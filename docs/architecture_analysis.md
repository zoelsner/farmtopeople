# Farm to People - Architecture Analysis & Refactoring Recommendations

## Executive Summary

After reviewing the codebase, I see a strong foundation with clear vision but opportunities for significant architectural improvements. The project has evolved organically with multiple scraper versions and needs consolidation to support the "Thursday Magic" vision effectively.

## Current State Analysis

### Strengths ✅
1. **Clear Product Vision**: The "Thursday Afternoon Magic" concept is well-defined
2. **Working Core Components**: Scraper, meal planner, and SMS integration are functional
3. **Data Persistence**: Supabase integration is in place
4. **AI Integration**: OpenAI-powered meal planning with validation/repair logic
5. **Detailed Extraction**: The scraper now captures prices, delivery dates, and quantities

### Areas for Improvement 🔧

#### 1. **Project Structure**
- **Current**: Flat structure with all files in root
- **Issue**: No separation of concerns, difficult to scale
- **Files scattered**: Multiple scraper versions in archive folder

#### 2. **Code Duplication**
- **8 different scraper versions** in archive folder
- Each slightly different, no clear "best" version
- `farmbox_optimizer.py` has incomplete box scraping logic

#### 3. **Lack of Abstraction**
- Direct playwright calls throughout
- No data models or schemas
- Business logic mixed with implementation details

#### 4. **Missing Automation**
- No Thursday scheduler implemented
- Manual trigger required for all operations
- No background job processing

#### 5. **Incomplete Integration**
- Server references `farmbox_optimizer.scan_farm_box()` which doesn't exist
- Meal planner expects specific JSON structure not guaranteed by scraper
- No error handling between components

## Recommended Architecture

### 1. **Project Structure Refactor**

```
farmtopeople/
├── src/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── models.py           # Pydantic models for all data
│   │   ├── config.py           # Configuration management
│   │   └── exceptions.py       # Custom exceptions
│   ├── scraping/
│   │   ├── __init__.py
│   │   ├── base.py            # Abstract scraper class
│   │   ├── cart_scraper.py    # Cart-specific logic
│   │   ├── box_scraper.py     # Box customization logic
│   │   └── utils.py           # Scraping utilities
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── meal_planner.py    # Meal generation
│   │   ├── validator.py       # Plan validation
│   │   └── prompts.py         # Prompt templates
│   ├── messaging/
│   │   ├── __init__.py
│   │   ├── sms_handler.py     # Twilio integration
│   │   ├── templates.py       # Message templates
│   │   └── flows.py           # Conversation flows
│   ├── scheduling/
│   │   ├── __init__.py
│   │   ├── thursday_monitor.py # Thursday automation
│   │   └── tasks.py           # Background tasks
│   ├── database/
│   │   ├── __init__.py
│   │   ├── client.py          # Supabase wrapper
│   │   └── repositories.py    # Data access layer
│   └── api/
│       ├── __init__.py
│       ├── server.py          # FastAPI app
│       ├── routes.py          # API endpoints
│       └── dependencies.py    # Dependency injection
├── tests/
│   └── ... (test structure mirrors src)
├── scripts/
│   ├── migrate_data.py        # One-time migration
│   └── setup_db.py           # Database setup
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── .env.example
├── pyproject.toml             # Modern Python packaging
├── README.md
└── docs/
    ├── architecture.md
    └── api.md
```

### 2. **Core Data Models**

```python
# src/core/models.py
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime
from decimal import Decimal

class CartItem(BaseModel):
    """Individual item in cart"""
    name: str
    type: Literal["box", "individual"]
    quantity: int
    unit: str  # "pieces", "dozen", "bunch"
    price: Decimal
    is_customizable: bool = False
    sub_items: List['BoxSubItem'] = []

class BoxSubItem(BaseModel):
    """Item within a box"""
    name: str
    quantity: int
    is_selected: bool = True
    is_alternative: bool = False

class CartSummary(BaseModel):
    """Complete cart state"""
    user_id: str
    scraped_at: datetime
    delivery_date: datetime
    delivery_day: str
    subtotal: Decimal
    delivery_fee: Decimal
    credits: Decimal
    total: Decimal
    items: List[CartItem]

class UserPreferences(BaseModel):
    """User cooking preferences"""
    dietary_restrictions: List[str] = []
    dislikes: List[str] = []
    cooking_confidence: Literal["beginner", "moderate", "expert"] = "moderate"
    preferred_time: Literal["quick", "standard", "ambitious"] = "standard"
    household_size: int = 2

class MealPlan(BaseModel):
    """Generated meal plan"""
    user_id: str
    week_of: datetime
    cart_summary: CartSummary
    meals: List['Meal']
    shopping_addons: List[str]
    
class Meal(BaseModel):
    """Individual meal suggestion"""
    id: str
    title: str
    base_time: int
    complexity: Literal["quick", "standard", "ambitious"]
    uses_ingredients: List[str]
    needs_additionally: List[str]
    instructions: Dict[str, List[str]]  # quick/standard/ambitious versions
    tips: List[str]
```

### 3. **Scraper Consolidation**

```python
# src/scraping/base.py
from abc import ABC, abstractmethod
from playwright.sync_api import Page, BrowserContext
from typing import Optional
import logging

class BaseScraper(ABC):
    """Abstract base class for all scrapers"""
    
    def __init__(self, context: BrowserContext, logger: Optional[logging.Logger] = None):
        self.context = context
        self.logger = logger or logging.getLogger(__name__)
        self.page: Optional[Page] = None
    
    @abstractmethod
    async def scrape(self, user_credentials: dict) -> dict:
        """Main scraping logic"""
        pass
    
    async def login(self, email: str, password: str) -> bool:
        """Shared login logic"""
        # Consolidated from working version
        pass
    
    async def safe_click(self, selector: str) -> bool:
        """Reliable click helper"""
        # Your existing safe_click logic
        pass

# src/scraping/cart_scraper.py
class CartScraper(BaseScraper):
    """Handles cart and checkout scraping"""
    
    async def scrape(self, user_credentials: dict) -> CartSummary:
        await self.login(user_credentials['email'], user_credentials['password'])
        await self.navigate_to_cart()
        
        items = await self.extract_cart_items()
        summary = await self.extract_cart_summary()
        
        return CartSummary(
            items=items,
            **summary
        )
    
    async def extract_cart_items(self) -> List[CartItem]:
        """Extract all cart items with proper quantity parsing"""
        # Your enhanced extraction logic here
        pass
```

### 4. **Thursday Automation**

```python
# src/scheduling/thursday_monitor.py
import asyncio
from datetime import datetime, time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

class ThursdayMonitor:
    """Handles Thursday afternoon automation"""
    
    def __init__(self, db_client, scraper_factory, meal_planner, sms_handler):
        self.db = db_client
        self.scraper_factory = scraper_factory
        self.meal_planner = meal_planner
        self.sms = sms_handler
        self.scheduler = AsyncIOScheduler()
    
    def start(self):
        """Initialize scheduled jobs"""
        # Thursday 2 PM - Check box lock
        self.scheduler.add_job(
            self.check_all_users,
            CronTrigger(day_of_week='thu', hour=14, minute=0),
            id='box_lock_check'
        )
        
        # Thursday 3 PM - Send preview
        self.scheduler.add_job(
            self.send_previews,
            CronTrigger(day_of_week='thu', hour=15, minute=0),
            id='send_previews'
        )
        
        # Thursday 6 PM - Send full plans
        self.scheduler.add_job(
            self.send_full_plans,
            CronTrigger(day_of_week='thu', hour=18, minute=0),
            id='send_plans'
        )
        
        self.scheduler.start()
    
    async def check_all_users(self):
        """Process all active users"""
        users = await self.db.get_active_users()
        
        for user in users:
            try:
                await self.process_user(user)
            except Exception as e:
                self.logger.error(f"Failed to process user {user.id}: {e}")
```

### 5. **Enhanced Server Architecture**

```python
# src/api/server.py
from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager
from .dependencies import get_db, get_scraper, get_meal_planner

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle"""
    # Start Thursday monitor on startup
    monitor = ThursdayMonitor(...)
    monitor.start()
    yield
    # Cleanup
    monitor.stop()

app = FastAPI(lifespan=lifespan)

# src/api/routes.py
@router.post("/webhooks/sms")
async def handle_sms(
    request: TwilioWebhookRequest,
    db: Database = Depends(get_db),
    tasks: BackgroundTasks = BackgroundTasks()
):
    """Handle incoming SMS with proper dependency injection"""
    user = await db.get_user_by_phone(request.From)
    
    if not user and "new" in request.Body.lower():
        # Start onboarding flow
        return await start_onboarding(request.From)
    
    # Route to appropriate handler
    return await route_message(user, request.Body, tasks)
```

### 6. **Configuration Management**

```python
# src/core/config.py
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Centralized configuration"""
    # API Keys
    openai_api_key: str
    twilio_account_sid: str
    twilio_auth_token: str
    twilio_phone_number: str
    supabase_url: str
    supabase_key: str
    
    # Scraping
    browser_headless: bool = True
    browser_timeout: int = 30000
    persistent_browser_data: str = "./browser_data"
    
    # Scheduling
    thursday_preview_time: str = "15:00"
    thursday_plan_time: str = "18:00"
    
    # Features
    enable_thursday_automation: bool = True
    enable_mms_images: bool = False
    
    class Config:
        env_file = ".env"

settings = Settings()
```

## Migration Plan

### Phase 1: Foundation (Week 1)
1. **Create new project structure**
2. **Define all Pydantic models**
3. **Consolidate scraper logic** into single, reliable version
4. **Set up proper testing framework**

### Phase 2: Core Refactor (Week 2)
1. **Migrate scraping logic** to new architecture
2. **Refactor meal planner** with proper interfaces
3. **Implement data repository pattern**
4. **Add comprehensive error handling**

### Phase 3: Automation (Week 3)
1. **Implement Thursday scheduler**
2. **Add background job processing**
3. **Create monitoring dashboard**
4. **Set up proper logging**

### Phase 4: Enhancement (Week 4)
1. **Add visual PDF generation**
2. **Implement preference learning**
3. **Create admin interface**
4. **Performance optimization**

## Key Improvements

### 1. **Reliability**
- Single source of truth for scraping logic
- Proper error handling and retries
- Graceful degradation

### 2. **Maintainability**
- Clear separation of concerns
- Type safety with Pydantic
- Comprehensive testing

### 3. **Scalability**
- Background job processing
- Caching layer
- Database connection pooling

### 4. **Observability**
- Structured logging
- Metrics collection
- Error tracking

## Next Steps

1. **Start with models**: Define your data structures first
2. **Consolidate scrapers**: Pick the best parts from each version
3. **Build incrementally**: Don't try to refactor everything at once
4. **Test continuously**: Add tests as you refactor

## Conclusion

The current codebase has all the right pieces but needs architectural refinement to achieve the "Thursday Magic" vision reliably and at scale. The proposed refactor will provide:

- **Better user experience** through reliability
- **Easier maintenance** through clear structure
- **Faster feature development** through proper abstractions
- **Scalability** for growth beyond 5 users

The investment in this refactor will pay dividends as you scale from prototype to production.
