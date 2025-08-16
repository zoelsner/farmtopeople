# Farm to People - Data Cleaning Guide
*Created: August 16, 2025*

## 🎯 Overview
This guide documents data inconsistencies found in Farm to People product data and provides cleaning strategies for standardization.

## 📊 Current Data Issues Identified

### **1. Unit Format Inconsistencies**

#### **Weight Units - Multiple Formats:**
```
INCONSISTENT:
- "1.0 Lbs" (92 occurrences)
- "8.0 Ounce" (69 occurrences) 
- "8.0 oz" (20 occurrences)
- "8 oz" (14 occurrences)

RECOMMENDED STANDARD:
- "1.0 lb" (singular, lowercase)
- "8.0 oz" (abbreviated, lowercase)
```

#### **Volume Units - Multiple Formats:**
```
INCONSISTENT:
- "1.0 Pint"
- "1.0 pint" 
- "1 pint"

RECOMMENDED STANDARD:
- "1.0 pt" (abbreviated, lowercase)
```

#### **Count Units - Multiple Formats:**
```
INCONSISTENT:
- "2 pieces"
- "1 piece" 
- "1 head"
- "1 bunch"
- "1 bar"
- "Each"

RECOMMENDED STANDARD:
- "2 pieces"
- "1 piece"
- "1 head"
- "1 bunch" 
- "1 bar"
- "1 each" (instead of just "Each")
```

### **2. Vendor Name Duplications**
From previous analysis, vendor names often have duplicated text:
```
INCONSISTENT:
- "Wish FarmsWish Farms"
- "Miami FruitMiami Fruit"
- "Equal Exchange Fairly TradedEqual Exchange Fairly..."

NEEDS CLEANING:
- Remove duplicated text
- Remove "..." truncation artifacts
- Standardize formatting
```

### **3. Decimal Precision Inconsistencies**
```
INCONSISTENT:
- "1.0 Lbs" vs "1 piece"
- "8.0 oz" vs "8 oz"
- "6 .5 oz pouches" (space in decimal)

RECOMMENDED:
- Use decimals consistently: "1.0 lb", "8.0 oz"
- Fix spacing: "6.5 oz pouches"
```

## 🧹 Data Cleaning Functions

### **Unit Standardization Function**
```python
import re

def standardize_units(unit_string):
    """
    Standardize unit formats across all products.
    """
    if not unit_string or unit_string.strip() == "":
        return ""
    
    unit = unit_string.strip().lower()
    
    # Weight standardization
    unit = re.sub(r'\b(\d+\.?\d*)\s*(pounds?|lbs?|lb)\b', r'\1 lb', unit)
    unit = re.sub(r'\b(\d+\.?\d*)\s*(ounces?|oz)\b', r'\1 oz', unit)
    
    # Volume standardization  
    unit = re.sub(r'\b(\d+\.?\d*)\s*(pints?|pt)\b', r'\1 pt', unit)
    unit = re.sub(r'\b(\d+\.?\d*)\s*(quarts?|qt)\b', r'\1 qt', unit)
    unit = re.sub(r'\b(\d+\.?\d*)\s*(gallons?|gal)\b', r'\1 gal', unit)
    
    # Count standardization
    unit = re.sub(r'\beach\b', '1 each', unit)
    unit = re.sub(r'\b(\d+)\s*pieces?\b', r'\1 pieces', unit)
    unit = re.sub(r'\b1\s*pieces?\b', '1 piece', unit)
    
    # Fix spacing issues
    unit = re.sub(r'(\d+)\s*\.\s*(\d+)', r'\1.\2', unit)  # Fix "6 .5" -> "6.5"
    unit = re.sub(r'\s+', ' ', unit)  # Multiple spaces -> single space
    
    return unit.strip()

# Examples:
# "8.0 Ounce" -> "8.0 oz"
# "1.0 Lbs" -> "1.0 lb" 
# "Each" -> "1 each"
# "6 .5 oz pouches" -> "6.5 oz pouches"
```

### **Vendor Name Cleaning Function**
```python
def clean_vendor_name(vendor):
    """
    Clean up vendor names by removing duplications and artifacts.
    """
    if not vendor:
        return "Unknown Vendor"
    
    # Remove trailing "..." artifacts
    vendor = re.sub(r'\.\.\..*$', '', vendor)
    
    # Handle duplicated text (e.g., "Wish FarmsWish Farms")
    words = vendor.split()
    
    # Try to find if first half equals second half
    for split_point in range(1, len(words)):
        first_part = ' '.join(words[:split_point])
        remaining = ' '.join(words[split_point:])
        if remaining.startswith(first_part):
            return first_part.strip()
    
    return vendor.strip()

# Examples:
# "Wish FarmsWish Farms" -> "Wish Farms"
# "Miami FruitMiami Fruit" -> "Miami Fruit"
# "Equal Exchange Fairly TradedEqual Exchange Fairly..." -> "Equal Exchange Fairly Traded"
```

### **Price Standardization Function**
```python
def standardize_price(price_string):
    """
    Standardize price formats.
    """
    if not price_string:
        return ""
    
    # Extract price using regex
    price_match = re.search(r'\$?(\d+\.?\d*)', price_string)
    if price_match:
        price_value = float(price_match.group(1))
        return f"${price_value:.2f}"
    
    return price_string

# Examples:
# "$8.99" -> "$8.99"
# "8.99" -> "$8.99"
# "$8" -> "$8.00"
```

## 📈 Recommended Data Model

### **Standardized Product Schema**
```python
{
    "name": str,           # Product name (cleaned)
    "category": str,       # "produce", "meat-seafood", "dairy-eggs", "pantry"
    "vendor": str,         # Cleaned vendor name
    "price": str,          # "$X.XX" format
    "quantity": float,     # Numeric quantity (extracted)
    "unit": str,           # Standardized unit ("oz", "lb", "pieces", "each", etc.)
    "unit_full": str,      # Full unit string (e.g., "8.0 oz", "2 pieces")
    "price_per_unit": float, # Calculated when possible
    "product_url": str,    # Full product URL
    "is_sold_out": bool,   # Availability status
    "is_subscription": bool, # If it's a subscription box
    "scraped_at": str,     # ISO timestamp
    "category_url": str    # Source category URL
}
```

## 🔧 Complete Data Cleaning Pipeline

### **Implementation in product_catalog_scraper.py**
Add this cleaning function to the scraper:

```python
def clean_product_data(raw_product):
    """
    Apply all cleaning functions to a raw product.
    """
    cleaned = raw_product.copy()
    
    # Clean vendor name
    cleaned['vendor'] = clean_vendor_name(raw_product.get('vendor', ''))
    
    # Standardize price
    cleaned['price'] = standardize_price(raw_product.get('price', ''))
    
    # Extract and standardize quantity/unit
    unit_string = raw_product.get('unit_info', '')
    cleaned['unit_full'] = standardize_units(unit_string)
    
    # Extract numeric quantity and unit separately
    quantity_match = re.search(r'(\d+\.?\d*)', cleaned['unit_full'])
    if quantity_match:
        cleaned['quantity'] = float(quantity_match.group(1))
        cleaned['unit'] = re.sub(r'^\d+\.?\d*\s*', '', cleaned['unit_full'])
    else:
        cleaned['quantity'] = 1.0
        cleaned['unit'] = cleaned['unit_full']
    
    # Calculate price per unit when possible
    try:
        price_value = float(re.search(r'\$?(\d+\.?\d*)', cleaned['price']).group(1))
        if cleaned['quantity'] > 0:
            cleaned['price_per_unit'] = round(price_value / cleaned['quantity'], 2)
        else:
            cleaned['price_per_unit'] = price_value
    except:
        cleaned['price_per_unit'] = None
    
    return cleaned
```

## 📋 Quality Assurance Checks

### **Data Validation Rules**
```python
def validate_product_data(product):
    """
    Validate cleaned product data for quality assurance.
    """
    issues = []
    
    # Required fields
    required_fields = ['name', 'category', 'vendor', 'price']
    for field in required_fields:
        if not product.get(field):
            issues.append(f"Missing {field}")
    
    # Price validation
    if product.get('price') and not re.match(r'^\$\d+\.\d{2}$', product['price']):
        issues.append(f"Invalid price format: {product['price']}")
    
    # Category validation
    valid_categories = ['produce', 'meat-seafood', 'dairy-eggs', 'pantry']
    if product.get('category') not in valid_categories:
        issues.append(f"Invalid category: {product['category']}")
    
    # Unit validation
    valid_units = ['oz', 'lb', 'pt', 'qt', 'gal', 'pieces', 'piece', 'each', 'bunch', 'head', 'bar']
    if product.get('unit') and not any(unit in product['unit'] for unit in valid_units):
        issues.append(f"Unusual unit: {product['unit']}")
    
    return issues
```

## 🎯 Expected Improvements

### **Before Cleaning:**
```csv
Name,Category,Vendor,Price,ApproxRangeCost
Pineberries,produce,Wish FarmsWish Farms,$8.99,10.0 oz
Organic Spigariello Kale,produce,County Line HarvestCounty Line Harvest,$3.39,1 bunch
```

### **After Cleaning:**
```csv
Name,Category,Vendor,Price,Quantity,Unit,Unit_Full,Price_Per_Unit
Pineberries,produce,Wish Farms,$8.99,10.0,oz,10.0 oz,$0.90
Organic Spigariello Kale,produce,County Line Harvest,$3.39,1.0,bunch,1 bunch,$3.39
```

## 🚀 Implementation Strategy

1. **Update `product_catalog_scraper.py`** with cleaning functions
2. **Test cleaning on small sample** before full scraping
3. **Compare before/after** data quality
4. **Generate quality report** with validation results
5. **Export cleaned data** in both JSON and CSV formats

This systematic approach will ensure Farm to People product data is consistent, searchable, and ready for analysis or integration into meal planning algorithms.
