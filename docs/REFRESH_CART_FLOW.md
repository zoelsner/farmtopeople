# Refresh Cart Complete Flow Documentation

## Timeline: What Happens When You Click "Refresh Cart"

### T+0ms: User Clicks Button
- **Action**: User clicks "Refresh Cart" button in dashboard
- **Location**: `dashboard.html` line ~2800
- **Function**: `refreshCart()` is called
- **State Changes**:
  - Loading spinner starts
  - Progress timer begins counting
  - Cart section hidden, loading section shown

### T+0-100ms: API Call Initiated
- **Endpoint**: `POST /api/analyze-cart`
- **Payload**:
  ```javascript
  {
    phone: userPhone,
    force_refresh: true  // Forces new scrape
  }
  ```
- **Server**: `server.py` line ~1750 `analyze_cart_api()` function

### T+100ms-16s: Scraping Phase (PARALLEL START)
- **Function**: `comprehensive_scraper.py` `main()` function
- **Timeline**:
  - T+100ms: Browser launches
  - T+1.5s: Navigate to farmtopeople.com
  - T+4s: Login completes
  - T+8s: Cart modal opens
  - T+8-15s: Scrape individual items & customizable boxes
  - T+15s: Extract delivery date
  - T+16s: Return scraped data
- **Output**: Complete cart JSON with categories

### T+16s: Data Processing (PARALLEL OPERATIONS)

#### Branch A: Swap Generation (T+16s-18s)
- **Function**: `generate_smart_swaps()` in `server.py`
- **Process**:
  1. Categorize current items (protein/produce/grocery)
  2. Find alternatives in same category
  3. Return 3 swaps per category
- **Output**: Category-aware swap suggestions

#### Branch B: Meal Generation (T+16s-25s)
- **Function**: `generate_meal_suggestions()` in `server.py`
- **Process**:
  1. Build GPT-5 prompt with cart items
  2. Add user preferences (if any)
  3. Request 5 meals with 20g+ protein
  4. Parse GPT response
- **Output**: 5 meal suggestions with protein counts

#### Branch C: Add-on Generation (T+25s-27s)
- **Function**: `generate_meal_addons()` in `server.py`
- **Waits for**: Meals to complete
- **Process**:
  1. Analyze gaps in generated meals
  2. Check what's NOT in cart/swaps
  3. Suggest 2-3 complementary items
- **Output**: Smart add-on suggestions

### T+27s: Data Assembly & Caching
- **Location**: `server.py` line ~1850
- **Operations** (PARALLEL):
  1. **Redis Cache** (2hr TTL):
     - Cart data → `cart:{phone}`
     - Meals → `meals:{phone}`
     - Add-ons → included in response
  2. **Supabase Save** (7 day retention):
     - `save_cart_analysis()` function
     - Stores everything for persistence

### T+28s: Response to Frontend
- **Response Structure**:
  ```json
  {
    "success": true,
    "cart_data": {...},
    "meal_suggestions": [...],
    "add_ons": [...],
    "swaps": [...],
    "delivery_date": "Sun, Sep 21",
    "processing_time": 28.2
  }
  ```

### T+28-29s: UI Update
- **Location**: `dashboard.html` line ~2900
- **Updates**:
  1. Hide loading spinner
  2. Render meal cards (2x2 grid)
  3. Display swaps by category
  4. Show add-ons with prices
  5. Update delivery date
  6. Stop progress timer

## Performance Breakdown

| Phase | Duration | Can Optimize? |
|-------|----------|--------------|
| Scraping | 16s | ✅ Session caching could reduce to 8s |
| Swaps | 2s | ✅ Already fast |
| Meals (GPT-5) | 9s | ⚠️ Model dependent |
| Add-ons | 2s | ✅ Already fast |
| Caching | 1s | ✅ Already fast |
| **Total** | **~28-30s** | Could reach 20s with session cache |

## Key Insights

1. **Parallel Processing**: Swaps and meals run simultaneously after scraping
2. **Add-ons Wait**: Add-ons must wait for meals to identify gaps
3. **Bottleneck**: GPT-5 meal generation (9s) is the longest single operation
4. **Scraping**: Currently 16s but could be 8s with session caching
5. **Data Persistence**: Both Redis (fast access) and Supabase (long-term) storage

## Error Handling

- **Scraper Timeout**: 120s timeout, falls back to cached data
- **GPT Failure**: Returns mock meals if API fails
- **Network Issues**: Retries 3x with exponential backoff
- **Cache Miss**: Falls back to database, then fresh scrape

## Future Optimizations

1. **Browser Session Caching** (save 8s)
   - Keep browser logged in between scrapes
   - Skip login flow entirely

2. **Parallel GPT Calls** (save 3-4s)
   - Generate meals in 2-3 parallel calls
   - Aggregate results

3. **Preemptive Scraping**
   - Scrape at 3am daily when cart updates
   - Serve from cache during day

4. **WebSocket Updates**
   - Stream progress to UI in real-time
   - Show "Scraping... → Generating meals... → Finding add-ons..."