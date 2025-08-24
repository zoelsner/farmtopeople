"""
Product catalog management for Farm to People meal planning.
Handles product matching, pricing lookups, and catalog operations.

Architecture Notes:
- LOCAL: Reads from CSV file (farmtopeople_products.csv)
- PRODUCTION: Should query from Supabase product_catalog table
- Includes fuzzy matching for AI-generated suggestions → real products

TODO for Production:
1. Cache full catalog in memory on server start (958 products is small)
2. Implement periodic refresh from Supabase
3. Add product availability checking
"""

import os
import json
import pandas as pd
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher


# Configuration
USE_SUPABASE = os.getenv("USE_SUPABASE", "false").lower() == "true"
PRODUCT_CATALOG_FILE = os.getenv(
    "PRODUCT_CATALOG_FILE", 
    "/Users/zach/Projects/farmtopeople/data/farmtopeople_products.csv"
)

# Cache for catalog data to avoid repeated file reads
_catalog_cache = None
_catalog_cache_time = None


def get_product_catalog() -> Dict[str, Dict[str, str]]:
    """
    Returns the complete product catalog with caching.
    
    LOCAL: Reads from CSV file
    PRODUCTION: Would query Supabase and cache in memory
    
    Returns:
        Dict mapping product name → {name, price, unit, vendor, category}
    """
    global _catalog_cache, _catalog_cache_time
    from datetime import datetime, timedelta
    
    # Check cache (refresh every 5 minutes in production)
    if _catalog_cache is not None:
        if _catalog_cache_time and datetime.now() - _catalog_cache_time < timedelta(minutes=5):
            return _catalog_cache
    
    catalog = {}
    
    if USE_SUPABASE:
        # TODO: Query Supabase for product catalog
        # from file_utils import get_data_source_client
        # client = get_data_source_client()
        # result = client.table('product_catalog').select('*').execute()
        # for product in result.data:
        #     catalog[product['name']] = {
        #         'name': product['name'],
        #         'price': product['price'],
        #         'unit': product['unit'],
        #         'vendor': product['vendor'],
        #         'category': product['category']
        #     }
        pass
    else:
        # Local CSV implementation
        try:
            if os.path.exists(PRODUCT_CATALOG_FILE):
                df = pd.read_csv(PRODUCT_CATALOG_FILE)
                for _, row in df.iterrows():
                    name = str(row.get('name', '')).strip()
                    if name and name != 'nan':
                        catalog[name] = {
                            'name': name,
                            'price': str(row.get('price', 'Price TBD')),
                            'unit': str(row.get('unit', 'item')),
                            'vendor': str(row.get('vendor', 'Unknown')),
                            'category': str(row.get('category', 'general'))
                        }
                print(f"💰 Loaded {len(catalog)} products from catalog")
        except Exception as e:
            print(f"⚠️ Error loading product catalog: {e}")
    
    # Update cache
    _catalog_cache = catalog
    _catalog_cache_time = datetime.now()
    
    return catalog


def get_curated_items_list() -> List[str]:
    """
    Returns a curated list of common Farm to People items.
    Used as fallback when catalog is unavailable.
    
    This list focuses on items commonly needed for meal planning.
    """
    return [
        # Proteins
        "Boneless, Skinless Chicken Breast",
        "Boneless, Skinless Chicken Thighs", 
        "Bone-in Chicken Thighs",
        "100% Grass-fed Ground Beef",
        "Ground Turkey",
        "Wild Salmon Fillet",
        "Black Sea Bass",
        
        # Fresh Produce
        "Organic Lemons",
        "Organic Limes",
        "Garlic",
        "Fresh Ginger",
        "Yellow Onions",
        "Red Onions",
        "Scallions",
        
        # Herbs
        "Fresh Basil",
        "Fresh Cilantro",
        "Fresh Parsley",
        "Fresh Thyme",
        "Fresh Rosemary",
        
        # Pantry Essentials
        "Extra Virgin Olive Oil",
        "Coconut Oil",
        "Sea Salt",
        "Black Pepper",
        "Organic Quinoa",
        "Brown Rice"
    ]


def fuzzy_match_product(
    suggestion: str, 
    threshold: float = 0.6
) -> Optional[Dict[str, str]]:
    """
    Finds the best matching product from catalog using fuzzy matching.
    
    Args:
        suggestion: AI-generated product suggestion
        threshold: Minimum similarity score (0-1)
    
    Returns:
        Best matching product dict or None
    """
    catalog = get_product_catalog()
    if not catalog:
        return None
    
    best_match = None
    best_score = 0
    suggestion_lower = suggestion.lower()
    
    for product_name, product_info in catalog.items():
        # Calculate similarity
        score = SequenceMatcher(None, suggestion_lower, product_name.lower()).ratio()
        
        # Boost score for exact substring matches
        if suggestion_lower in product_name.lower():
            score += 0.2
        
        if score > best_score and score >= threshold:
            best_score = score
            best_match = product_info
    
    return best_match


def find_best_catalog_match(suggestion: str) -> Optional[Tuple[str, str, str]]:
    """
    Enhanced matching specifically for post-processing AI suggestions.
    
    Args:
        suggestion: Text that might contain a product name
    
    Returns:
        Tuple of (product_name, price, unit) or None
    """
    catalog = get_product_catalog()
    if not catalog:
        return None
    
    suggestion_lower = suggestion.lower()
    best_match = None
    best_score = 0
    
    for product_name, product_info in catalog.items():
        product_lower = product_name.lower()
        
        # Check for exact or near-exact matches
        if product_lower in suggestion_lower or suggestion_lower in product_lower:
            score = 0.9
        else:
            # Fuzzy matching
            score = SequenceMatcher(None, suggestion_lower, product_lower).ratio()
        
        # Special handling for proteins (boost common protein matches)
        if any(protein in product_lower for protein in ['chicken', 'beef', 'turkey', 'salmon', 'fish']):
            if any(protein in suggestion_lower for protein in ['chicken', 'beef', 'turkey', 'salmon', 'fish']):
                score += 0.1
        
        if score > best_score:
            best_score = score
            best_match = (
                product_info['name'],
                product_info['price'],
                product_info['unit']
            )
    
    # Only return if confidence is high enough
    if best_score >= 0.5:
        return best_match
    
    return None


def add_pricing_to_analysis(analysis_text: str) -> str:
    """
    Post-processes GPT-5 analysis to add real FTP pricing.
    This avoids sending the full catalog to the AI (cost optimization).
    
    Strategy:
    1. Look for product mentions in the analysis
    2. Match them to catalog items
    3. Replace with exact names and prices
    
    Args:
        analysis_text: Raw analysis from GPT-5
    
    Returns:
        Analysis with pricing information added
    """
    catalog = get_product_catalog()
    if not catalog:
        print("⚠️ Product catalog not available, skipping pricing")
        return analysis_text
    
    # Hardcoded preferred proteins (user specified these exact products)
    preferred_proteins = {
        "chicken breast": ("Locust Point Farm Boneless Skinless Chicken Breast", "$12.99", "0.7-1 lb"),
        "boneless, skinless chicken breast": ("Locust Point Farm Boneless Skinless Chicken Breast", "$12.99", "0.7-1 lb"),
        "chicken thighs": ("Locust Point Farm Boneless Skinless Chicken Thighs", "$8.99", "0.6-1 lb"),
        "boneless, skinless chicken thighs": ("Locust Point Farm Boneless Skinless Chicken Thighs", "$8.99", "0.6-1 lb"),
        "bone-in chicken thighs": ("Locust Point Farm Bone-in Chicken Thighs", "$7.59", "0.7-1 lb"),
        "ground beef": ("100% Grass-fed Ground Beef", "$9.99", "1.0 lb"),
        "ground turkey": ("White Ground Turkey", "$8.99", "1.0 lb"),
        "salmon": ("Wild Salmon Fillet", "$16.99", "8 oz"),
    }
    
    # Common fresh items that need pricing
    common_items = {
        "garlic": ("Garlic", "$2.99", "1 bulb"),
        "lemon": ("Organic Lemons", "$1.99", "2 pieces"),
        "lemons": ("Organic Lemons", "$1.99", "2 pieces"),
        "lime": ("Organic Limes", "$1.99", "2 pieces"),
        "limes": ("Organic Limes", "$1.99", "2 pieces"),
        "basil": ("Fresh Basil", "$3.99", "1 bunch"),
        "cilantro": ("Fresh Cilantro", "$2.99", "1 bunch"),
        "ginger": ("Fresh Ginger", "$3.99", "4 oz"),
    }
    
    enhanced_text = analysis_text
    replacements_made = []
    
    # Process preferred proteins first (exact replacements)
    for generic_name, (full_name, price, unit) in preferred_proteins.items():
        if generic_name in enhanced_text.lower():
            # Create the replacement with pricing
            replacement = f"{full_name} ({price}, {unit})"
            
            # Try to find and replace in context
            import re
            # Look for patterns like "chicken breast" or "Chicken Breast"
            pattern = re.compile(re.escape(generic_name), re.IGNORECASE)
            if pattern.search(enhanced_text):
                enhanced_text = pattern.sub(replacement, enhanced_text, count=1)
                replacements_made.append(generic_name)
    
    # Process common fresh items
    for item_key, (full_name, price, unit) in common_items.items():
        if item_key in enhanced_text.lower() and item_key not in replacements_made:
            # Look for the item in various contexts
            patterns = [
                f"fresh {item_key}",
                f"1 {item_key}",
                f"2 {item_key}",
                item_key.capitalize(),
                item_key
            ]
            
            for pattern in patterns:
                if pattern in enhanced_text or pattern.lower() in enhanced_text.lower():
                    replacement = f"{full_name} ({price})"
                    enhanced_text = enhanced_text.replace(pattern, replacement, 1)
                    replacements_made.append(item_key)
                    break
    
    if replacements_made:
        print(f"💰 Added pricing for: {', '.join(replacements_made)}")
    
    return enhanced_text


def get_product_by_name(product_name: str) -> Optional[Dict[str, str]]:
    """
    Direct lookup of a product by exact name.
    
    Args:
        product_name: Exact product name to find
    
    Returns:
        Product dict or None if not found
    """
    catalog = get_product_catalog()
    return catalog.get(product_name)


def search_products_by_category(category: str) -> List[Dict[str, str]]:
    """
    Returns all products in a given category.
    
    Args:
        category: Category name (produce, meat-seafood, dairy-eggs, pantry)
    
    Returns:
        List of products in that category
    """
    catalog = get_product_catalog()
    return [
        product for product in catalog.values() 
        if product.get('category', '').lower() == category.lower()
    ]