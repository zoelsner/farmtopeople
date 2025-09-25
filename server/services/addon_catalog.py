"""
Add-On Product Catalog
======================
Fixed mapping of essential add-on products from Farm to People.
Focus on fresh herbs, aromatics, and finishing touches that elevate meals.

Last Updated: September 2025
Based on: farmtopeople_products.csv with full vendor and quantity details
"""

# Expanded 40-item catalog with fresh ingredients people often forget
ADDON_CATALOG = {
    # Fresh Herbs (12 items) - The stars of the show!
    'cilantro': {
        'name': 'Organic Cilantro',
        'vendor': 'Grown in California',
        'price': '$2.99',
        'unit': '1 bunch',
        'category': 'produce',
        'reason_template': 'Essential herb for Mexican, Asian, and Indian dishes'
    },
    'parsley': {
        'name': 'Organic Italian Parsley',
        'vendor': 'Sun Sprout Farm',
        'price': '$3.29',
        'unit': '1 bunch',
        'category': 'produce',
        'reason_template': 'Universal garnish and flavor brightener'
    },
    'basil': {
        'name': 'Organic Fresh Basil',
        'vendor': 'Sun Sprout Farm',
        'price': '$4.99',
        'unit': '1 bunch',
        'category': 'produce',
        'reason_template': 'Italian and Thai cuisine essential'
    },
    'scallions': {
        'name': 'Organic Scallions',
        'vendor': 'Sun Sprout Farm',
        'price': '$3.99',
        'unit': '1 bunch',
        'category': 'produce',
        'reason_template': 'Finishing touch for Asian dishes and salads'
    },
    'dill': {
        'name': 'Organic Dill',
        'vendor': 'Lancaster Farm Fresh',
        'price': '$3.49',
        'unit': '1 bunch',
        'category': 'produce',
        'reason_template': 'Perfect for fish, potatoes, and pickled vegetables'
    },
    'rosemary': {
        'name': 'Organic Bunched Rosemary',
        'vendor': 'Sucker Brook Farm',
        'price': '$4.99',
        'unit': '1 bunch',
        'category': 'produce',
        'reason_template': 'Aromatic herb for roasts and potatoes'
    },
    'thyme': {
        'name': 'Organic Bunched Thyme',
        'vendor': 'Lancaster Farm Fresh',
        'price': '$4.99',
        'unit': '1 bunch',
        'category': 'produce',
        'reason_template': 'Classic herb for soups, stews, and roasts'
    },
    'sage': {
        'name': 'Organic Bunched Sage',
        'vendor': 'Lancaster Farm Fresh',
        'price': '$4.49',
        'unit': '1 bunch',
        'category': 'produce',
        'reason_template': 'Fall dishes and brown butter sauces'
    },
    'mint': {
        'name': 'Organic Bunched Spearmint',
        'vendor': 'Sun Sprout Farm',
        'price': '$3.99',
        'unit': '1 bunch',
        'category': 'produce',
        'reason_template': 'Middle Eastern dishes, drinks, and fruit salads'
    },
    'chives': {
        'name': 'Organic Chives',
        'vendor': 'Soli Organic',
        'price': '$3.49',
        'unit': '0.5 oz',
        'category': 'produce',
        'reason_template': 'Delicate onion flavor for eggs and potatoes'
    },
    'microgreens': {
        'name': 'Organic Microgreens',
        'vendor': 'Agrarian Feast',
        'price': '$8.99',
        'unit': '1.25 oz',
        'category': 'produce',
        'reason_template': 'Restaurant-quality garnish'
    },
    'oregano': {
        'name': 'Fresh Oregano',
        'vendor': 'Local Farms',
        'price': '$3.99',
        'unit': '1 bunch',
        'category': 'produce',
        'reason_template': 'Mediterranean and Mexican cooking essential'
    },

    # Fresh Aromatics & Produce (8 items)
    'lemons': {
        'name': 'Organic Lemons',
        'vendor': 'California Citrus',
        'price': '$1.99',
        'unit': '1 piece',
        'category': 'produce',
        'reason_template': 'Brightens everything with acidity'
    },
    'limes': {
        'name': 'Organic Limes',
        'vendor': 'California Citrus',
        'price': '$1.49',
        'unit': '1 piece',
        'category': 'produce',
        'reason_template': 'Essential for Mexican and Thai dishes'
    },
    'garlic': {
        'name': 'Organic Garlic',
        'vendor': 'Local Farms',
        'price': '$1.00',
        'unit': '1 head',
        'category': 'produce',
        'reason_template': 'Foundation for savory dishes worldwide'
    },
    'ginger': {
        'name': 'Organic Ginger Root',
        'vendor': 'Imported Fresh',
        'price': '$1.99',
        'unit': '4 oz',
        'category': 'produce',
        'reason_template': 'Asian stir-fries and marinades'
    },
    'fresno_peppers': {
        'name': 'Red Fresno Peppers',
        'vendor': 'Sunny Harvest',
        'price': '$3.99',
        'unit': '12 oz',
        'category': 'produce',
        'reason_template': 'Adds moderate heat and color'
    },
    'yellow_onions': {
        'name': 'Yellow Onions',
        'vendor': 'Dagele Brothers',
        'price': '$1.79',
        'unit': '3 pieces (1 lb)',
        'category': 'produce',
        'reason_template': 'Base for soups, stews, and sautés'
    },
    'shallots': {
        'name': 'Shallots',
        'vendor': 'Local Farms',
        'price': '$2.49',
        'unit': '6 oz',
        'category': 'produce',
        'reason_template': 'Mild sweetness for dressings and sauces'
    },
    'avocados': {
        'name': 'Organic Hass Avocados',
        'vendor': 'Equal Exchange',
        'price': '$2.50',
        'unit': '1 piece',
        'category': 'produce',
        'reason_template': 'Creamy addition to any meal'
    },

    # Dairy & Cheese (8 items)
    'greek_yogurt': {
        'name': 'Greek Yogurt',
        'vendor': 'Maple Hill Creamery',
        'price': '$7.99',
        'unit': '16 oz',
        'category': 'dairy',
        'reason_template': 'Creamy base for sauces and toppings'
    },
    'feta': {
        'name': 'Salty Sea Feta',
        'vendor': 'Narragansett Creamery',
        'price': '$6.99',
        'unit': '8 oz',
        'category': 'dairy',
        'reason_template': 'Mediterranean salads and grain bowls'
    },
    'goat_cheese': {
        'name': 'Plain Goat Cheese',
        'vendor': 'FireFly Farms',
        'price': '$4.99',
        'unit': '4 oz',
        'category': 'dairy',
        'reason_template': 'Creamy tang for salads and pasta'
    },
    'ricotta': {
        'name': 'Ricotta',
        'vendor': 'Narragansett Creamery',
        'price': '$7.49',
        'unit': '16 oz',
        'category': 'dairy',
        'reason_template': 'Lasagna, stuffed shells, and toast topping'
    },
    'sour_cream': {
        'name': 'Sour Cream',
        'vendor': 'Ronnybrook Farm',
        'price': '$7.69',
        'unit': '16 oz',
        'category': 'dairy',
        'reason_template': 'Tacos, baked potatoes, and dips'
    },
    'butter': {
        'name': 'Cultured Butter',
        'vendor': 'Vermont Creamery',
        'price': '$5.99',
        'unit': '8 oz',
        'category': 'dairy',
        'reason_template': 'Rich foundation for sautéing'
    },
    'parmesan': {
        'name': 'Parmigiano Reggiano',
        'vendor': "Murray's Cheese",
        'price': '$10.99',
        'unit': '5.3 oz',
        'category': 'dairy',
        'reason_template': 'Finishing touch for pasta and salads'
    },
    'eggs': {
        'name': 'Pasture Raised Eggs',
        'vendor': 'Local Farms',
        'price': '$6.99',
        'unit': '1 dozen',
        'category': 'dairy',
        'reason_template': 'Quick protein for any meal'
    },

    # Cooking Liquids & Sauces (8 items)
    'chicken_broth': {
        'name': 'Chicken Bone Broth',
        'vendor': 'Yellow Bell Farm',
        'price': '$14.99',
        'unit': '24 oz',
        'category': 'pantry',
        'reason_template': 'Rich base for soups and risottos'
    },
    'coconut_milk': {
        'name': 'Organic Coconut Milk',
        'vendor': 'Native Forest',
        'price': '$5.59',
        'unit': '13.5 oz',
        'category': 'pantry',
        'reason_template': 'Thai curries and creamy sauces'
    },
    'tahini': {
        'name': 'Sesame Tahini',
        'vendor': 'Soom Foods',
        'price': '$9.99',
        'unit': '11 oz',
        'category': 'pantry',
        'reason_template': 'Middle Eastern sauces and dressings'
    },
    'capers': {
        'name': 'Non-Pareil Capers',
        'vendor': 'Mina',
        'price': '$4.99',
        'unit': '7 oz',
        'category': 'pantry',
        'reason_template': 'Mediterranean pop of flavor'
    },
    'pesto': {
        'name': 'Basil Pesto',
        'vendor': 'Farm To People Kitchen',
        'price': '$9.99',
        'unit': '8 oz',
        'category': 'pantry',
        'reason_template': 'Instant pasta sauce or sandwich spread'
    },
    'chimichurri': {
        'name': 'Chimichurri',
        'vendor': 'Farm To People Kitchen',
        'price': '$7.99',
        'unit': '8 oz',
        'category': 'pantry',
        'reason_template': 'Argentinian herb sauce for grilled meats'
    },
    'harissa': {
        'name': 'Harissa with Preserved Lemon',
        'vendor': 'New York Shuk',
        'price': '$16.99',
        'unit': '10 oz',
        'category': 'pantry',
        'reason_template': 'North African spice paste for depth'
    },
    'miso': {
        'name': 'Mellow Red Miso',
        'vendor': 'Rhapsody Natural Foods',
        'price': '$14.49',
        'unit': '16 oz',
        'category': 'pantry',
        'reason_template': 'Umami depth for soups and marinades'
    },

    # Bread & Carbs (4 items)
    'bread': {
        'name': 'Fresh Artisan Bread',
        'vendor': 'Local Bakery',
        'price': '$5.99',
        'unit': '1 loaf',
        'category': 'pantry',
        'reason_template': 'Essential for soups, sandwiches, and toast'
    },
    'tortillas': {
        'name': 'Corn Tortillas',
        'vendor': 'All Souls Tortilleria',
        'price': '$4.99',
        'unit': '12 pack',
        'category': 'pantry',
        'reason_template': 'Taco Tuesday essential'
    },
    'pita': {
        'name': 'Fresh Pita Bread',
        'vendor': "Issa's",
        'price': '$4.49',
        'unit': '6 pack',
        'category': 'pantry',
        'reason_template': 'Mediterranean wraps and dipping'
    },
    'naan': {
        'name': 'Garlic Naan',
        'vendor': 'Local Bakery',
        'price': '$4.99',
        'unit': '4 pack',
        'category': 'pantry',
        'reason_template': 'Indian curries need this'
    },

    # Nuts & Seeds (4 items)
    'walnuts': {
        'name': 'Raw Walnuts',
        'vendor': 'Boxford Bakehouse',
        'price': '$10.59',
        'unit': '6 oz',
        'category': 'pantry',
        'reason_template': 'Salad crunch and baking'
    },
    'pine_nuts': {
        'name': 'Pine Nuts',
        'vendor': 'Imported',
        'price': '$19.99',
        'unit': '4 oz',
        'category': 'pantry',
        'reason_template': 'Pesto and Mediterranean dishes'
    },
    'pepitas': {
        'name': 'Roasted Pumpkin Seeds',
        'vendor': 'Stony Brook',
        'price': '$4.99',
        'unit': '3 oz',
        'category': 'pantry',
        'reason_template': 'Salad topping and snacking'
    },
    'sesame_seeds': {
        'name': 'Toasted Sesame Seeds',
        'vendor': 'Asian Pantry',
        'price': '$6.99',
        'unit': '4 oz',
        'category': 'pantry',
        'reason_template': 'Asian dishes and everything bagel seasoning'
    }
}


def get_addon_product(item_key: str) -> dict:
    """
    Get a specific add-on product by key.

    Args:
        item_key: Key from ADDON_CATALOG (e.g., 'lemons', 'garlic')

    Returns:
        Product dict with name, price, category, or None if not found
    """
    return ADDON_CATALOG.get(item_key)


def get_available_addon_keys() -> list:
    """
    Get list of all available add-on keys for AI to choose from.

    Returns:
        List of strings like ['lemons', 'garlic', 'basil', ...]
    """
    return list(ADDON_CATALOG.keys())


def map_suggestions_to_products(ai_suggestions: list) -> list:
    """
    Map AI suggestions to actual products from the catalog.

    Args:
        ai_suggestions: List of dicts with 'item' and 'reason' keys

    Returns:
        List of product dicts with name, vendor, price, unit, category, and reason
    """
    products = []

    for suggestion in ai_suggestions:
        item_key = suggestion.get('item', '').lower().replace(' ', '_')

        # Try to find the product in our catalog
        if item_key in ADDON_CATALOG:
            product = ADDON_CATALOG[item_key].copy()
            # Add the item key for deduplication
            product['item'] = item_key
            # Use AI's specific reason or fall back to template
            product['reason'] = suggestion.get('reason', product.get('reason_template', ''))
            # Remove template from final output
            if 'reason_template' in product:
                del product['reason_template']
            products.append(product)

    return products