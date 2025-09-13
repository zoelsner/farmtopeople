# 🔥 QUICK PHONE DEBUGGING GUIDE

## IF CART SHOWS OLD DATA

### 1. Check what's in the database
```bash
source venv/bin/activate
python -c "
import sys; sys.path.insert(0, 'server')
import supabase_client as db
phone = '4254955323'  # YOUR PHONE HERE
cart = db.get_latest_cart_data(phone)
if cart:
    print(f'✅ Cart from: {cart.get(\"scraped_at\")}')
    data = cart.get('cart_data', {})
    boxes = data.get('customizable_boxes', [])
    if boxes:
        print('First box items:')
        for item in boxes[0].get('selected_items', [])[:3]:
            print(f'  - {item.get(\"name\")}')
else:
    print('❌ No cart found')
"
```

### 2. Check phone format in localStorage
Open browser console (F12) and run:
```javascript
localStorage.getItem('userPhone')
// Should be 10 digits, no spaces or symbols
```

### 3. Fix truncated phone (9 digits)
```javascript
// In browser console
localStorage.setItem('userPhone', '4254955323')  // Full 10 digits
location.reload()
```

## IF USER NOT FOUND

### Check all phone formats in DB
```bash
python -c "
import sys; sys.path.insert(0, 'server')
import supabase_client as db
from services.phone_service import get_phone_variants
phone = '4254955323'  # YOUR PHONE
variants = get_phone_variants(phone)
print(f'Checking formats: {variants}')
for v in variants:
    user = db.get_user_by_phone(v)
    if user:
        print(f'✅ Found with: {v}')
        break
else:
    print('❌ No user with any format')
"
```

## IF SCRAPER RUNS BUT DATA DOESN'T UPDATE

### 1. Check latest scraper output
```bash
ls -lt farm_box_data/*.json | head -3
# Look for today's date
```

### 2. Force update database with latest cart
```bash
python update_cart_db.py
# This updates the database with latest JSON
```

### 3. Verify update worked
```bash
python -c "
import sys; sys.path.insert(0, 'server')
import supabase_client as db
cart = db.get_latest_cart_data('4254955323')
print(f'Cart updated: {cart.get(\"scraped_at\") if cart else \"NOT FOUND\")}')
"
```

## EMERGENCY FIXES

### Clear everything and start fresh
```javascript
// Browser console
localStorage.clear()
location.href = '/onboard?phone=4254955323'
```

### Force specific phone format
```javascript
// Browser console  
localStorage.setItem('userPhone', '4254955323')
window.getPhoneNumber = () => '4254955323'
```

### Check what analyze-cart is receiving
Open Network tab (F12), look for `/api/analyze-cart` request:
- Request payload should have `phone: "4254955323"` (10 digits)
- If 9 digits → localStorage has wrong number
- If +1 format → Frontend normalization issue

## THE GOLDEN RULE

**If phone number issues persist after these fixes, the problem is likely NOT the phone number.**

Check instead:
1. Is the scraper actually getting new data?
2. Is the database connection working?
3. Are credentials expired?
4. Is the cart actually different from last week?

---

**Remember:** Phone issues are now handled at database layer. If it's still broken after trying both formats, something else is wrong.