# Farm to People AI Assistant - Complete Implementation Guide

## Core Product Vision
**The Thursday Afternoon Magic**: Transform Farm to People's weekly box from a "what do I do with this?" moment into an exciting culinary adventure that starts before the box even arrives.

## The Killer Feature: Reverse Meal Planning
Instead of "here's a recipe, go buy ingredients" → "here's what's in your box, here's what you can make"

### Thursday Timing Strategy
```python
# Thursday 2PM: Box contents are locked for Saturday delivery
# Thursday 3PM: Our system scrapes and sends first preview
# Thursday 6PM: Dinner planning time - send enhanced suggestions
# Friday Morning: Final beautiful PDF with weekend prep tips
# Saturday: Delivery day excitement
```

## Technical Architecture

### Project Structure
```
farm-to-people-assistant/
├── backend/
│   ├── server.py                 # FastAPI main server
│   ├── scraper/
│   │   ├── farmbox_optimizer.py  # Playwright scraper
│   │   └── box_monitor.py        # Thursday afternoon scheduler
│   ├── ai_engine/
│   │   ├── meal_generator.py     # OpenAI recipe generation
│   │   ├── preference_learner.py # Implicit learning system
│   │   └── complexity_matcher.py # 25/35/45 min meal sorting
│   ├── visual_generator/
│   │   ├── pdf_builder.py        # ReportLab for PDFs
│   │   ├── meal_cards.py         # Pillow for image composites
│   │   └── templates/            # Visual templates
│   ├── messaging/
│   │   ├── sms_handler.py        # Twilio integration
│   │   └── mms_composer.py       # Visual message builder
│   └── database/
│       └── supabase_client.py    # User data & preferences
├── data/
│   ├── farmtopeople_products.csv # Master product list
│   ├── recipe_templates/         # Flexible recipe frameworks
│   └── visual_assets/           # Icons, backgrounds, etc.
└── config/
    └── .env                      # API keys
```

### Core Data Models
```python
from pydantic import BaseModel
from typing import List, Dict, Optional, Literal
from datetime import datetime

class ComplexityLevel(Literal["quick", "moderate", "ambitious"]):
    """25, 35, or 45 minutes"""
    pass

class BoxItem(BaseModel):
    """Single item from Farm to People box"""
    name: str
    category: str  # produce, dairy, protein, pantry
    quantity: str
    storage_tip: str
    use_by_priority: int  # 1-5, 1 being use first
    image_url: Optional[str]

class MealSuggestion(BaseModel):
    """A single meal suggestion"""
    id: str
    name: str
    base_time: int  # 25, 35, or 45
    complexity: ComplexityLevel
    hero_image: str
    uses_ingredients: List[str]  # from box
    needs_additionally: List[str]  # pantry items
    
    # The magic: optional enhancements
    quick_version: Dict  # 25 min version
    moderate_version: Dict  # 35 min version  
    ambitious_version: Dict  # 45 min version
    
    storage_tips: Dict[str, str]
    leftover_ideas: List[str]
    
class WeeklyPlan(BaseModel):
    """Thursday afternoon delivery"""
    user_id: str
    week_of: datetime
    box_contents: List[BoxItem]
    
    # 5 meals suggested, user picks 3-4
    meal_suggestions: List[MealSuggestion]
    
    # User's energy level this week
    energy_mode: Literal["tired", "normal", "ambitious"]
    
    # What they didn't use last week
    leftover_ingredients: List[str]
    
    # Personalization
    avoided_last_time: List[str]
    loved_last_time: List[str]
```

### The Thursday Scraper System
```python
import asyncio
from playwright.async_api import async_playwright
from datetime import datetime, timedelta
import schedule

class ThursdayBoxMonitor:
    """Monitors for box lock and triggers meal planning"""
    
    def __init__(self, supabase_client, twilio_client):
        self.db = supabase_client
        self.sms = twilio_client
        
    async def check_box_status(self, user_id: str):
        """Thursday 2PM check if box is locked"""
        user = self.db.get_user(user_id)
        
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            # Login to Farm to People
            await page.goto("https://farmtopeople.com/login")
            await page.fill("#email", user.ftp_email)
            await page.fill("#password", user.ftp_password)
            await page.click("button[type='submit']")
            
            # Navigate to upcoming delivery
            await page.goto("https://farmtopeople.com/my-deliveries")
            
            # Check if customization window is closed
            box_locked = await page.locator(".customization-closed").is_visible()
            
            if box_locked:
                # Scrape the final box contents
                box_contents = await self.scrape_box_contents(page)
                await browser.close()
                return box_contents
            
            await browser.close()
            return None
    
    async def scrape_box_contents(self, page):
        """Extract what's in their box"""
        box_items = []
        
        items = await page.locator(".box-item").all()
        for item in items:
            name = await item.locator(".item-name").text_content()
            quantity = await item.locator(".item-quantity").text_content()
            category = await item.get_attribute("data-category")
            image = await item.locator("img").get_attribute("src")
            
            box_items.append(BoxItem(
                name=name.strip(),
                category=category,
                quantity=quantity.strip(),
                image_url=image,
                storage_tip=self.get_storage_tip(name),
                use_by_priority=self.calculate_priority(name)
            ))
        
        return box_items
    
    def get_storage_tip(self, item_name: str) -> str:
        """Lookup storage tips from our database"""
        tips = {
            "lettuce": "Wrap in damp paper towel, store in crisper",
            "tomatoes": "Keep on counter until ripe, then refrigerate",
            "herbs": "Trim stems, place in water like flowers",
            # ... extensive database
        }
        return tips.get(item_name.lower(), "Store in cool, dry place")
```

### The AI Meal Generator
```python
from openai import OpenAI
import json

class ReverseMealPlanner:
    """Generates meals from available ingredients"""
    
    def __init__(self):
        self.client = OpenAI()
        
    async def generate_meal_suggestions(
        self, 
        box_contents: List[BoxItem],
        user_preferences: Dict,
        leftover_ingredients: List[str] = []
    ) -> List[MealSuggestion]:
        """The magic happens here"""
        
        # Build the prompt
        ingredients_list = [item.name for item in box_contents]
        if leftover_ingredients:
            ingredients_list = leftover_ingredients + ingredients_list
        
        prompt = f"""
        You are a creative chef specializing in seasonal, local cooking.
        
        Available ingredients (use as many as possible):
        {json.dumps(ingredients_list)}
        
        User preferences:
        - Avoided last time: {user_preferences.get('avoided', [])}
        - Loved last time: {user_preferences.get('loved', [])}
        - Dietary restrictions: {user_preferences.get('restrictions', [])}
        - Cooking confidence: {user_preferences.get('confidence', 'moderate')}
        
        Generate 5 meal suggestions that:
        1. Use multiple ingredients from the list
        2. Feel exciting and seasonal
        3. Have 3 complexity levels:
           - Quick (25 min): Simple, one-pot, minimal prep
           - Moderate (35 min): Some technique, multiple components
           - Ambitious (45 min): Restaurant-style, impressive
        
        For each meal, provide:
        - A craveable name
        - Which box ingredients it uses
        - What pantry staples are needed
        - How to adapt it for each time level
        - One "chef's secret" tip
        - Leftover transformation idea
        
        Format as JSON matching MealSuggestion schema.
        Make it feel like an adventure, not a chore.
        """
        
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        meals = json.loads(response.choices[0].message.content)
        return [MealSuggestion(**meal) for meal in meals['suggestions']]
    
    def rank_by_user_energy(
        self, 
        meals: List[MealSuggestion], 
        energy: str
    ) -> List[MealSuggestion]:
        """Sort meals by user's current energy level"""
        if energy == "tired":
            # Prioritize quick versions
            return sorted(meals, key=lambda m: m.base_time)
        elif energy == "ambitious":
            # Show off the fancy versions
            return sorted(meals, key=lambda m: -m.base_time)
        else:
            # Balanced mix
            return meals
```

### The Visual PDF Generator
```python
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Image, Paragraph, Table
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from PIL import Image as PILImage, ImageDraw, ImageFont
import io

class BeautifulMealPDF:
    """Creates the Thursday afternoon visual feast"""
    
    def generate_weekly_guide(
        self, 
        plan: WeeklyPlan,
        user_name: str
    ) -> bytes:
        """Create the PDF that gets people excited"""
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        
        # Cover page with this week's hero ingredients
        cover = self.create_cover_page(plan.box_contents, user_name)
        story.append(cover)
        
        # The "Choose Your Adventure" page
        adventure_page = self.create_energy_selector(plan.meal_suggestions)
        story.append(adventure_page)
        
        # Individual meal cards with complexity toggles
        for meal in plan.meal_suggestions[:3]:  # Top 3 meals
            meal_card = self.create_meal_card(meal)
            story.append(meal_card)
        
        # The "Waste Warrior" page - using everything
        waste_warrior = self.create_zero_waste_guide(plan.box_contents)
        story.append(waste_warrior)
        
        # Storage cheat sheet
        storage_guide = self.create_storage_visual(plan.box_contents)
        story.append(storage_guide)
        
        doc.build(story)
        return buffer.getvalue()
    
    def create_meal_card(self, meal: MealSuggestion) -> Image:
        """Beautiful meal card with time toggles"""
        
        # Create base card image
        card = PILImage.new('RGB', (600, 800), 'white')
        draw = ImageDraw.Draw(card)
        
        # Hero image (top 40%)
        # ... image placement code
        
        # Three complexity boxes
        boxes = [
            {"time": "25 min", "label": "QUICK", "color": "#4CAF50"},
            {"time": "35 min", "label": "MODERATE", "color": "#FF9800"},
            {"time": "45 min", "label": "AMBITIOUS", "color": "#9C27B0"}
        ]
        
        for i, box in enumerate(boxes):
            x = 50 + (i * 180)
            y = 400
            draw.rounded_rectangle(
                [x, y, x+160, y+80], 
                radius=10, 
                fill=box['color']
            )
            draw.text(
                (x+80, y+40), 
                f"{box['label']}\n{box['time']}", 
                anchor="mm"
            )
        
        # Ingredients used from box (with checkmarks)
        y_offset = 500
        for ingredient in meal.uses_ingredients:
            draw.text((50, y_offset), f"✓ {ingredient}", fill="green")
            y_offset += 25
        
        # Chef's tip in a callout box
        tip_box = self.create_tip_callout(meal.chef_tip)
        card.paste(tip_box, (50, 650))
        
        return self.pil_to_reportlab(card)
```

### The Thursday SMS Flow
```python
from twilio.rest import Client
from datetime import datetime
import asyncio

class ThursdayAfternoonSMS:
    """The engagement driver"""
    
    def __init__(self, twilio_client, pdf_generator, meal_planner):
        self.sms = twilio_client
        self.pdf_gen = pdf_generator
        self.planner = meal_planner
    
    async def send_thursday_preview(self, user):
        """3PM Thursday - First excitement builder"""
        
        box_contents = await self.scrape_current_box(user)
        meals = await self.planner.generate_meal_suggestions(
            box_contents, 
            user.preferences
        )
        
        # Create teaser message
        message = f"""
        🌟 {user.name}, your Farm to People box is locked in!
        
        This week's stars:
        • {box_contents[0].name} (perfect for...)
        • {box_contents[1].name} (try it in...)
        • {box_contents[2].name} (chef's favorite!)
        
        How's your energy this week?
        Reply: 1=Tired 😴, 2=Normal 😊, 3=Ambitious 🚀
        
        (Your personalized meal plan arrives in 3 hours)
        """
        
        self.sms.messages.create(
            to=user.phone,
            from_=TWILIO_PHONE,
            body=message
        )
    
    async def send_evening_plan(self, user, energy_level):
        """6PM Thursday - Full meal plan"""
        
        # Generate beautiful PDF
        pdf = await self.pdf_gen.generate_weekly_guide(
            plan=user.current_plan,
            user_name=user.name
        )
        
        # Upload to temporary storage
        pdf_url = await self.upload_pdf(pdf)
        
        # Create composite image for MMS
        preview_image = self.create_week_preview_image(user.current_plan)
        
        message = f"""
        🍽️ Your adventures await!
        
        Based on your {energy_level} energy:
        
        Tonight: {user.current_plan.meal_suggestions[0].name}
        → {25 if energy_level=='tired' else 35} minutes
        
        Tomorrow: {user.current_plan.meal_suggestions[1].name}
        → Perfect for Friday night
        
        📱 Full visual guide: {pdf_url}
        
        Reply SWAP to see alternatives
        Reply SHOP to add missing pantry items
        """
        
        self.sms.messages.create(
            to=user.phone,
            from_=TWILIO_PHONE,
            body=message,
            media_url=[preview_image]
        )
```

### The Learning System
```python
class ImplicitPreferenceLearner:
    """Learns without asking annoying questions"""
    
    def track_interaction(self, user_id: str, event: Dict):
        """Every interaction teaches us something"""
        
        events_to_track = {
            "opened_pdf": 0.1,  # Mild interest
            "clicked_meal": 0.3,  # Stronger interest
            "replied_energy": 0.2,  # Engagement
            "swapped_meal": -0.2,  # Didn't like suggestion
            "made_meal": 0.5,  # Actually cooked it
            "requested_again": 1.0,  # Loved it
            "skipped_week": -0.5,  # Something wrong
        }
        
        if event['type'] in events_to_track:
            weight = events_to_track[event['type']]
            
            # Update preferences
            if 'meal_id' in event:
                self.update_meal_preference(user_id, event['meal_id'], weight)
            
            if 'ingredients' in event:
                for ingredient in event['ingredients']:
                    self.update_ingredient_preference(user_id, ingredient, weight)
    
    def update_meal_preference(self, user_id, meal_id, weight):
        """Adjust meal scoring based on interaction"""
        # Store in Supabase with decay over time
        self.db.upsert_preference({
            'user_id': user_id,
            'meal_id': meal_id,
            'weight': weight,
            'timestamp': datetime.now()
        })
```

## Implementation Roadmap

### Week 1: Foundation (This Week)
```python
# 1. Set up Thursday scheduler
schedule.every().thursday.at("14:00").do(check_all_boxes)
schedule.every().thursday.at("15:00").do(send_first_preview)
schedule.every().thursday.at("18:00").do(send_full_plans)

# 2. Basic scraper working
# 3. Simple meal generation (no AI yet, use templates)
# 4. Text-only SMS working
```

### Week 2: Intelligence
```python
# 1. OpenAI integration for meal generation
# 2. Basic PDF generation (no fancy graphics yet)
# 3. Energy level responses
# 4. Simple preference tracking
```

### Week 3: Visual Magic
```python
# 1. Beautiful PDF with meal cards
# 2. MMS preview images
# 3. Storage tips with icons
# 4. Leftover tracking
```

### Week 4: Learning & Optimization
```python
# 1. Implicit preference learning
# 2. Swap suggestions
# 3. Pantry integration
# 4. Success metrics dashboard
```

## Key Tools & Services

### Required APIs & Services
```python
# config/.env
OPENAI_API_KEY="sk-..."
TWILIO_ACCOUNT_SID="..."
TWILIO_AUTH_TOKEN="..."
TWILIO_PHONE_NUMBER="+1..."
SUPABASE_URL="https://....supabase.co"
SUPABASE_KEY="..."
CLOUDINARY_URL="..."  # For image hosting
```

### Python Dependencies
```python
# requirements.txt
fastapi==0.104.0
playwright==1.39.0
openai==1.3.0
twilio==8.10.0
supabase==2.0.0
pillow==10.1.0
reportlab==4.0.7
schedule==1.2.0
pydantic==2.5.0
python-dotenv==1.0.0
```

### Quick Start Commands
```bash
# Install everything
pip install -r requirements.txt
playwright install chromium

# Set up database
python scripts/setup_supabase.py

# Run the Thursday monitor
python backend/box_monitor.py

# Start the API server
uvicorn backend.server:app --reload
```

## The User Experience Flow

### Thursday 3PM - The Tease
"Your box is locked! This week features beautiful rainbow chard, heirloom tomatoes, and fresh mozzarella. How hungry are you feeling? 😋"

### Thursday 6PM - The Plan
"Based on your 'normal' energy, here are your top 3 meals:
1. **Summer Caprese Grain Bowl** (30 min)
2. **Rainbow Chard Shakshuka** (35 min)  
3. **Heirloom Tomato Tart** (40 min)

Each can be simplified to 25 min or leveled up to impress!"

### Friday Morning - The Reminder
"Weekend prep tip: Your herbs will last longer in water! Check your meal guide for the storage cheat sheet 🌿"

### Saturday Delivery - The Celebration
"Your box has arrived! Everything you need for tonight's Caprese Bowl is ready. Want the 5-minute prep-ahead tip?"

### Sunday Check-in - The Learning
"How did the Shakshuka turn out? Reply: 😍 Loved it, 👍 Good, or 🔄 Need alternatives"

## Success Metrics

```python
class SuccessTracker:
    """What we measure"""
    
    key_metrics = {
        "thursday_open_rate": "% who engage with Thursday message",
        "pdf_downloads": "% who view the full guide",
        "energy_responses": "% who reply with energy level",
        "meals_attempted": "% who report cooking suggested meals",
        "skip_rate_change": "Reduction in skipped weeks",
        "add_on_rate": "Increase in pantry item additions",
        "retention_3_month": "% still active after 3 months"
    }
    
    target_metrics = {
        "thursday_open_rate": 0.75,  # 75% engagement
        "pdf_downloads": 0.60,  # 60% view guide
        "meals_attempted": 0.50,  # 50% cook suggestions
        "skip_rate_change": -0.30,  # 30% fewer skips
        "retention_3_month": 0.70  # 70% retain
    }
```

## The Secret Sauce

**Why this works:**
1. **Anticipation > Delivery**: Thursday creates 2 days of excitement
2. **Choice > Assignment**: Users pick from suggestions, not prescribed meals
3. **Flexibility > Rigidity**: 25/35/45 minute options match real life
4. **Visual > Text**: Beautiful PDFs make cooking feel special
5. **Learning > Asking**: Track behavior, don't quiz users

**The Farm to People Advantage:**
- We start with what's actually available (reverse planning)
- We know what's seasonal and local (authenticity)
- We reduce waste (sustainability)
- We build cooking confidence (education)
- We make Thursday exciting (anticipation)

## Next Steps

1. **Test with your 5 users** using manual processes first
2. **Measure what resonates** (which meals, what timing, which complexity)
3. **Build the Thursday scraper** to automate box monitoring
4. **Create template meals** before adding AI generation
5. **Design one beautiful PDF** before building the generator
6. **Track every interaction** to build the learning system

Remember: **Start manual, learn what works, then automate.**

The goal isn't to build everything at once - it's to make Thursday afternoons magical for 5 people, learn what they love, then scale that magic.
