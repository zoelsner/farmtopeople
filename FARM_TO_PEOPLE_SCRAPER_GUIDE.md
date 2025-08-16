# Farm to People Scraper - Complete Guide

## Overview
This guide documents the complete scraping solution for Farm to People's customizable subscription boxes. The scraper extracts both **selected items** and **available alternatives** from the customize interface.

## Key Scripts

### 1. `simple_scraper.py` - Basic Cart Scraping
- **Purpose**: Scrapes selected items from cart sidebar (without clicking customize)
- **Use Case**: Quick extraction of what's currently selected
- **Output**: Selected items only

### 2. `customize_scraper.py` - Full Customize Interface Scraping  
- **Purpose**: Clicks CUSTOMIZE buttons and scrapes complete selection interface
- **Use Case**: Get both selected items AND available alternatives for swapping
- **Output**: Complete data with swap options

### 3. `weekly_summary_scraper.py` - Customer Weekly Summary Generator
- **Purpose**: Creates beautiful customer-friendly weekly summaries for texting/emailing
- **Use Case**: Send weekly box updates to customers before meal suggestions
- **Output**: Formatted markdown summary + raw data

### 4. `better_capture.py` - HTML Debugging Tool
- **Purpose**: Captures HTML from customize interface for debugging selectors
- **Use Case**: When selectors break or UI changes

## Technical Architecture

### Website Structure
```
farmtopeople.com/home
├── Cart Button (opens cart sidebar)
├── Cart Sidebar
│   ├── Box Items (articles)
│   │   ├── CUSTOMIZE Button
│   │   └── Sub-items List (selected items visible)
│   └── CUSTOMIZE Modal (when clicked)
│       ├── Selected Items (with quantity selectors)
│       └── Available Alternatives (with ADD buttons)
```

### Key CSS Selectors

#### Cart Navigation
- **Cart Button**: `div.cart-button.ml-auto.cursor-pointer`
- **Cart Items**: `article[class*='cart-order_cartOrderItem']`
- **CUSTOMIZE Button**: `button:has-text('CUSTOMIZE'), button:has-text('Customize')`

#### Customize Modal
- **Modal Container**: `aside[aria-label*='Customize']`
- **Item Articles**: `article[aria-label]`
- **Selected Items**: Items with `div[class*='quantity-selector']`
- **Available Items**: Items with `button:has-text('Add')`
- **Close Button**: `button:has-text('Close')`

#### Item Data Extraction
- **Item Name**: `aria-label` attribute on `<article>`
- **Producer**: `p[class*='producer'] a`
- **Unit Info**: `div[class*='item-details'] p`
- **Quantity**: `span[class*='quantity']` (for selected items)

## Complete Item Inventory

### Seasonal Produce Box - Small (14 total items)

#### ✅ Selected Items (7)
1. **Sugar Cube Cantaloupe** - Sunny Harvest - 1 piece
2. **Organic Sungold Cherry Tomatoes** - Sun Sprout Farm - 1 pint  
3. **Organic Red Fingerling Potatoes** - Sun Sprout Farm - 1.0 Lbs
4. **Organic Fairytale Eggplant** - Sun Sprout Farm - 8.0 oz
5. **Green Zucchini** - Reeves Farm - 2 pieces
6. **Organic Green Beans** - Lancaster Farm Fresh Cooperative - 12.0 oz
7. **Organic Romaine Lettuce** - Pedersen Farms - 1 head

#### 🔄 Available Alternatives (7)
1. **White Peaches** - Weaver's Orchard - 2 pieces
2. **Organic Jalapeno Peppers** - Lancaster Farm Fresh Cooperative - 5 pieces
3. **Asian Eggplant** - Sunny Harvest - 2 pieces
4. **Organic Red Kale** - Pedersen Farms - 1 bunch
5. **Slicing Cucumbers** - Reeves Farm - 2 pieces
6. **Red Onions** - Dagele Brothers Produce - 2 Lbs
7. **Yellow Onions** - Dagele Brothers Produce - 2.0 Lbs

### The Cook's Box - Paleo (19 total items)

#### ✅ Selected Items (11)
1. **Yellowfin Tuna** - Red's Best Seafood - 12 oz
2. **Ground Pork** - Heritage Foods - 1.0 Lbs
3. **Sugar Cube Cantaloupe** - Sunny Harvest - 1 piece
4. **White Donut Peaches** - Hurd Orchards - 1 pint
5. **Organic Bunched Orange Carrots** - Sun Sprout Farm - 1 bunch
6. **Organic Fairytale Eggplant** - Sun Sprout Farm - 8.0 oz
7. **Organic Red Kale** - Pedersen Farms - 1 bunch
8. **Organic Red Bell Peppers** - Halal Pastures - 3 pieces
9. **Slicing Cucumbers** - Reeves Farm - 2 pieces
10. **Green Zucchini** - Reeves Farm - 2 pieces
11. **Organic Heirloom Tomatoes** - Finger Foods Farm - 1.0 Lbs

#### 🔄 Available Alternatives (8)
1. **Bone-in, Skin-on Chicken Thighs** - Locust Point Farm - 0.7 - 1 lb
2. **Pork Belly** - Autumn's Harvest - 10-14 oz
3. **Organic Romaine Lettuce** - Pedersen Farms - 1 head
4. **White Peaches** - Weaver's Orchard - 2 pieces
5. **Organic Jalapeno Peppers** - Lancaster Farm Fresh Cooperative - 5 pieces
6. **Asian Eggplant** - Sunny Harvest - 2 pieces
7. **Red Onions** - Dagele Brothers Produce - 2 Lbs
8. **Yellow Onions** - Dagele Brothers Produce - 2.0 Lbs

## Item Categories Analysis

### By Category Type

#### 🍎 Fruits
- Sugar Cube Cantaloupe
- White Peaches  
- White Donut Peaches
- Organic Sungold Cherry Tomatoes
- Organic Heirloom Tomatoes

#### 🥬 Vegetables - Leafy Greens
- Organic Romaine Lettuce
- Organic Red Kale

#### 🥕 Vegetables - Root/Bulb
- Organic Red Fingerling Potatoes
- Organic Bunched Orange Carrots
- Red Onions
- Yellow Onions

#### 🍆 Vegetables - Other
- Organic Fairytale Eggplant
- Asian Eggplant
- Green Zucchini
- Organic Green Beans
- Organic Red Bell Peppers
- Organic Jalapeno Peppers
- Slicing Cucumbers

#### 🐟 Proteins - Seafood
- Yellowfin Tuna

#### 🐷 Proteins - Meat
- Ground Pork
- Bone-in, Skin-on Chicken Thighs
- Pork Belly

### By Producer

#### 🌾 **Sun Sprout Farm** (4 items)
- Organic Sungold Cherry Tomatoes
- Organic Red Fingerling Potatoes  
- Organic Fairytale Eggplant
- Organic Bunched Orange Carrots

#### 🌾 **Sunny Harvest** (2 items)
- Sugar Cube Cantaloupe
- Asian Eggplant

#### 🌾 **Reeves Farm** (3 items)
- Green Zucchini
- Slicing Cucumbers

#### 🌾 **Pedersen Farms** (2 items)
- Organic Romaine Lettuce
- Organic Red Kale

#### 🌾 **Lancaster Farm Fresh Cooperative** (2 items)
- Organic Green Beans
- Organic Jalapeno Peppers

#### 🌾 **Dagele Brothers Produce** (2 items)  
- Red Onions
- Yellow Onions

#### 🌾 **Other Producers** (1 item each)
- Weaver's Orchard: White Peaches
- Red's Best Seafood: Yellowfin Tuna
- Heritage Foods: Ground Pork
- Hurd Orchards: White Donut Peaches
- Halal Pastures: Organic Red Bell Peppers
- Finger Foods Farm: Organic Heirloom Tomatoes
- Locust Point Farm: Bone-in, Skin-on Chicken Thighs
- Autumn's Harvest: Pork Belly

## Usage Instructions

### Quick Start
```bash
# Activate virtual environment
source venv/bin/activate

# Get selected items only (fast)
python simple_scraper.py

# Get complete data with alternatives (comprehensive)
python customize_scraper.py

# Generate customer weekly summary (for texting/emailing)
python weekly_summary_scraper.py
```

### Output Files
- **Cart data**: `farm_box_data/box_contents_TIMESTAMP.json`
- **Customize data**: `farm_box_data/customize_results_TIMESTAMP.json`
- **Weekly summary**: `farm_box_data/weekly_customer_summary_TIMESTAMP.md`
- **Raw weekly data**: `farm_box_data/weekly_data_TIMESTAMP.json`
- **Debug HTML**: `farm_box_data/customize_page_TIMESTAMP.html`

## Troubleshooting

### Common Issues

1. **CUSTOMIZE button not clickable**
   - Issue: Button outside viewport
   - Solution: Script includes `scroll_into_view_if_needed()`

2. **Modal not loading**
   - Issue: Need more wait time
   - Solution: Increase `page.wait_for_timeout()` values

3. **Selectors not working**
   - Issue: Website UI changed
   - Solution: Run `better_capture.py` to get fresh HTML and update selectors

4. **Browser session expired**
   - Issue: Need to re-login
   - Solution: Delete `browser_data` folder and re-run

### Debugging Steps
1. Run `better_capture.py` to capture current HTML
2. Check console output for error messages
3. Verify selectors against captured HTML
4. Update selectors in script as needed

## Data Structure

### Selected Item Object
```json
{
  "name": "Sugar Cube Cantaloupe",
  "producer": "Sunny Harvest",
  "unit": "1 piece", 
  "quantity": 1,
  "selected": true
}
```

### Available Alternative Object
```json
{
  "name": "White Peaches",
  "producer": "Weaver's Orchard", 
  "unit": "2 pieces",
  "quantity": 0,
  "selected": false
}
```

### Complete Box Object
```json
{
  "selected_items": [...],
  "available_alternatives": [...],
  "total_items": 14,
  "selected_count": 7,
  "alternatives_count": 7,
  "box_name": "Seasonal Produce Box - Small",
  "box_index": 1
}
```

## Future Enhancements

### Potential Features
- **Price tracking**: Extract item prices
- **Nutrition data**: Scrape nutritional information  
- **Seasonal availability**: Track when items appear/disappear
- **Automated swapping**: Actually click ADD/REMOVE buttons
- **Email notifications**: Alert when preferred items become available

### Maintenance Notes
- Check selectors monthly for UI changes
- Update producer names if farms change
- Monitor for new box types
- Test after Farm to People website updates

## File Structure
```
farmtopeople/
├── FARM_TO_PEOPLE_SCRAPER_GUIDE.md  # This documentation
├── customize_scraper.py              # Main scraper (recommended)
├── simple_scraper.py                 # Basic cart scraper  
├── better_capture.py                 # HTML debugging tool
├── farm_box_data/                    # Output directory
│   ├── customize_results_*.json      # Customize scraper output
│   ├── box_contents_*.json           # Simple scraper output
│   └── *.html                        # Debug HTML captures
└── browser_data/                     # Persistent browser session
```

---

**Last Updated**: August 16, 2025  
**Status**: 🎉 **PRODUCTION READY - MAJOR SYSTEM OVERHAUL COMPLETE**

## 🚀 **MAJOR UPDATE - August 16, 2025**
**COMPREHENSIVE SCRAPING SYSTEM CLEANUP:**
- 🗑️ **Removed deprecated files**: `farmbox_optimizer.py`, `capture_customize.py`, `capture_html.py`, `full_scraper.py`, `cart_structure_analyzer.py`
- ✅ **Working scrapers confirmed**: All 5 production scrapers tested and documented
- 📚 **Documentation complete**: Created comprehensive guides, audit docs, and cleanup plans
- 🌿 **Git organized**: Branches created (`stable-scrapers` backup, `feature/customer-automation` for next phase)
- 🎯 **Ready for automation**: System prepared for Thursday Magic customer workflow

**Production Scrapers (Priority Order):**
1. `complete_cart_scraper.py` - **PRIMARY** (handles boxes + individual items + summaries)
2. `simple_scraper.py` - Fast box extraction
3. `weekly_summary_scraper.py` - Customer communication
4. `customize_scraper.py` - Alternative exploration  
5. `better_capture.py` - Debug tool

**Next Review**: Monthly or after website changes
