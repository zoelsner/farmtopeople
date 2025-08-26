# 📱 Business Flow & User Journey

**Last Updated:** August 26, 2025  
**Product:** Farm to People AI Meal Planning Assistant

## Executive Summary

Transform weekly Farm to People deliveries into personalized meal plans through SMS, learning preferences to reduce food waste and increase customer satisfaction.

## User Journey

### 1. **Onboarding** (First Time)
```
Customer receives box → Gets SMS invite → Completes preferences → Receives welcome meal plan
```

**Preference Collection (6 Steps):**
1. Phone number & household size
2. Dietary restrictions (allergies, no-pork, vegetarian)
3. Health goals (high-protein, low-carb, balanced)
4. Cooking preferences (quick meals, batch cooking)
5. Cuisine preferences (Mediterranean, Asian, comfort)
6. FTP login credentials (secure storage)

**What We Learn:**
- Household composition (affects portions)
- Foods to avoid (safety & preference)
- Nutritional priorities (protein goals)
- Time constraints (20-min dinners)
- Flavor profiles (spice tolerance)

### 2. **Weekly Planning Flow**

#### Tuesday - Cart Finalization
```
10am: Cart closes
11am: SMS: "Your cart is ready! Text PLAN for meals"
User: "plan"
System: [30 seconds processing]
11:01am: "Your meal plan is ready! 5 dinners, 22 servings"
11:02am: Link to detailed PDF
```

#### The SMS Conversation:
```
User: "plan"
Bot: "🔍 Looking up your account..."
Bot: "📦 Analyzing your cart..."
Bot: "🤖 Creating personalized meals..."
Bot: "✅ Your meal plan:
1. 15-Min Chicken Stir-Fry (35g protein)
2. Salmon + Vegetables (38g protein)
3. Mediterranean Bowl (28g protein)
4. Veggie Frittata (24g protein)
5. Beef Skillet (32g protein)

View full recipes: [link]
Need changes? Reply SWAP"
```

### 3. **The Meal Plan Document**

**Single-Page PDF Contains:**
- **Current Selections** - Everything in their cart
- **Smart Swaps** - Based on preferences
  - "Pork Chops → Chicken (you don't eat pork)"
  - "Add onions ($1.29) - needed for 4 meals"
- **5 Dinner Recipes** - Name, time, protein, servings
- **Premium Add-ons** - Upsell opportunities
- **Storage Guide** - Keep food fresh

**Design Philosophy:**
- Penny restaurant menu aesthetic
- No emojis or decorations
- Subtle blue accents (#4169E1)
- High information density
- Professional typography

### 4. **Modification Flow** (Planned)

```
User: "swap 2"
Bot: "Swap Salmon recipe with:
A) Sheet Pan Chicken (40g protein, 35 min)
B) Tofu Stir-Fry (22g protein, 20 min)
Reply A or B"

User: "A"
Bot: "✅ Updated! Sheet Pan Chicken replaced Salmon.
New plan: [link]"
```

### 5. **Post-Delivery**

#### Thursday - Delivery Day
```
2pm: "Your Farm Box was delivered! 
Tonight: Try the 15-min Chicken Stir-Fry
Prep tip: Chop vegetables while rice cooks"
```

#### Saturday - Weekend Cooking
```
10am: "Weekend cooking time! 
The Veggie Frittata (meal #3) is perfect for brunch
Makes great leftovers for Monday"
```

#### Sunday - Feedback
```
6pm: "How was your week of meals?
Quick survey: [link]
Your feedback helps us improve"
```

## Value Propositions

### For Customers:
1. **Save 3-5 hours** weekly on meal planning
2. **Reduce food waste** by 40%
3. **Hit nutrition goals** (30g+ protein)
4. **Try new recipes** matched to preferences
5. **Shop smarter** with swap suggestions

### For Farm to People:
1. **Increase retention** - Engaged customers stay longer
2. **Boost order value** - Premium add-on suggestions
3. **Reduce support tickets** - Proactive guidance
4. **Gather preferences** - Better box curation
5. **Create habit** - Weekly touchpoint

## Preference Intelligence

### What We Track:
```python
preferences = {
    # Explicit (from onboarding)
    'dietary_restrictions': ['no-pork', 'gluten-free'],
    'goals': ['high-protein', 'quick-dinners'],
    'household_size': 2,
    
    # Implicit (from behavior)
    'recipes_completed': ['Mediterranean Bowl', 'Stir-Fry'],
    'swaps_made': ['pork→chicken', 'kale→spinach'],
    'cooking_days': ['Tuesday', 'Thursday', 'Sunday'],
    'avg_cook_time': 25,
    
    # Derived (from analysis)
    'protein_target': 35,  # grams per meal
    'preferred_cuisines': ['Mediterranean', 'Asian'],
    'spice_tolerance': 'medium',
    'batch_cooker': False
}
```

### How Preferences Shape Output:

**High-Protein Goal:**
- Every meal shows protein content
- Meals under 30g get flagged
- Suggests protein add-ons
- Sorts by protein content

**Quick Dinners Goal:**
- Prioritizes sub-30 minute meals
- Shows prep shortcuts
- Suggests batch cooking
- Highlights one-pan meals

**No Pork Preference:**
- Automatically swaps bacon → turkey bacon
- Flags pork items in cart
- Never suggests pork recipes
- Offers halal/kosher alternatives

## Business Rules

### Meal Generation:
1. **Always 5 meals** (dinner focus)
2. **Minimum 30g protein** for high-protein users
3. **Maximum 30 minutes** for quick-dinner users
4. **Use 80%+ of cart** items
5. **Show clear swaps** for preferences

### SMS Communication:
1. **Immediate acknowledgment** (<2 seconds)
2. **Progress updates** during processing
3. **Complete in <30 seconds** total
4. **Always include help text**
5. **Provide clear next actions**

### Cart Analysis:
1. **Flag preference conflicts** (pork for non-pork eaters)
2. **Identify missing essentials** (onions, garlic)
3. **Calculate protein coverage**
4. **Note storage priorities** (use fish first)
5. **Suggest value adds** under $10

## Success Metrics

### Engagement:
- **Activation Rate:** 75% complete onboarding
- **Weekly Active:** 65% request meal plans
- **Modification Rate:** 30% make swaps
- **Completion Rate:** 70% cook 3+ meals

### Quality:
- **Preference Match:** 90% respect restrictions
- **Protein Target:** 85% hit 30g+ goal
- **Time Target:** 90% under 30 minutes
- **Cart Usage:** 80% ingredients used

### Business:
- **Retention Lift:** +20% vs control
- **Order Value:** +$12 average
- **Support Reduction:** -30% food questions
- **NPS Increase:** +15 points

## Customer Segments

### 1. **Busy Professionals** (35%)
- Need: Quick weeknight dinners
- Focus: 20-minute meals, meal prep
- Messaging: "Dinner in 20 minutes"

### 2. **Health Optimizers** (30%)
- Need: Hit protein/nutrition goals
- Focus: Macros, clean eating
- Messaging: "35g protein per meal"

### 3. **Family Planners** (25%)
- Need: Feed family efficiently
- Focus: Kid-friendly, batch cooking
- Messaging: "Feeds family of 4"

### 4. **Culinary Explorers** (10%)
- Need: Try new cuisines
- Focus: Unique recipes, techniques
- Messaging: "Restaurant-quality at home"

## Competitive Advantages

1. **Real Cart Integration** - Not generic recipes
2. **True Personalization** - Learns preferences
3. **SMS Simplicity** - No app needed
4. **Instant Value** - 30-second response
5. **Professional Design** - Restaurant-quality PDFs

## Risk Mitigation

### Technical Risks:
- **Scraper breaks:** Fallback to cached data
- **GPT fails:** Pre-generated backup plans
- **SMS delays:** Email backup delivery

### Business Risks:
- **Low adoption:** Incentivize with credits
- **Poor recipes:** Human review queue
- **Privacy concerns:** Clear data policy

## Future Enhancements

### Phase 2 (Q2 2025):
- Voice interactions ("Alexa, what's for dinner?")
- Shopping list integration
- Leftover management
- Wine pairings

### Phase 3 (Q3 2025):
- Family member preferences
- Nutrition tracking integration
- Video recipe guides
- Community recipe sharing

### Phase 4 (Q4 2025):
- Predictive cart building
- Seasonal menu planning
- Local restaurant partnerships
- Cooking class integration

## Implementation Status

### ✅ Complete:
- Onboarding flow with preference capture
- Cart scraping (all box types)
- GPT-5 meal generation
- SMS integration with Vonage
- Basic PDF generation
- Preference storage in Supabase

### 🚧 In Progress:
- Penny-style PDF design
- Preference-based swaps
- Help text in SMS

### 📝 Planned This Week:
- Redis conversation state
- Modification handlers
- Instant acknowledgments
- Production deployment

### 🔮 Future:
- Cart value calculations
- Weekly feedback loop
- A/B testing framework
- Analytics dashboard

---

*This flow optimizes for: Speed (30 seconds), Simplicity (SMS), and Value (personalized to preferences).*