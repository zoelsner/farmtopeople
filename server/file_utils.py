"""
File utilities for Farm to People meal planning system.
Handles data loading, file operations, and cart data processing.

Architecture Notes:
- LOCAL: Reads from JSON files in farm_box_data/ directory
- PRODUCTION (Railway): Should read from Supabase tables:
  - cart_analyses: Stores full cart analysis results
  - user_carts: Stores scraped cart data per user
  - product_catalog: Master product list with pricing
  
TODO for Production:
1. Replace file operations with Supabase queries
2. Use user_id instead of timestamps for data retrieval
3. Cache frequently accessed data in Redis/memory
"""

import os
import json
import glob
from typing import Dict, List, Union, Optional, Tuple
from datetime import datetime


# Configuration for data source switching
USE_SUPABASE = os.getenv("USE_SUPABASE", "false").lower() == "true"
FARM_BOX_DATA_DIR = os.getenv("FARM_BOX_DATA_DIR", "../farm_box_data")


def get_data_source_client():
    """
    Returns the appropriate data client based on environment.
    
    LOCAL: Returns None (uses file system)
    PRODUCTION: Returns Supabase client
    
    TODO: Implement Supabase client initialization here
    """
    if USE_SUPABASE:
        # TODO: Initialize and return Supabase client
        # from supabase_client import get_supabase_client
        # return get_supabase_client()
        pass
    return None


def get_latest_cart_file(directory: str = FARM_BOX_DATA_DIR, user_id: str = None) -> Union[str, None]:
    """
    Finds the most recent cart_contents JSON file.
    
    LOCAL: Searches directory for latest cart_contents_*.json
    PRODUCTION: Would query Supabase for user's latest cart data
    
    Args:
        directory: Local directory path (ignored in production)
        user_id: User identifier for Supabase queries (ignored locally)
    
    Returns:
        File path (local) or cart data dict (production)
    """
    if USE_SUPABASE and user_id:
        # TODO: Implement Supabase query
        # client = get_data_source_client()
        # result = client.table('user_carts').select('*').eq('user_id', user_id).order('created_at', desc=True).limit(1).execute()
        # return result.data[0] if result.data else None
        pass
    
    # Local file system implementation
    try:
        cart_files = glob.glob(os.path.join(directory, "cart_contents_*.json"))
        if not cart_files:
            return None
        return max(cart_files, key=os.path.getmtime)
    except Exception as e:
        print(f"Error finding cart file: {e}")
        return None


def get_latest_box_file(directory: str = FARM_BOX_DATA_DIR, box_name_slug: str = "") -> Union[str, None]:
    """
    Finds the most recent JSON file for a specific box type.
    
    LOCAL: Searches for {box_name_slug}_*.json files
    PRODUCTION: Would query for specific box data
    
    Args:
        directory: Local directory path
        box_name_slug: Box identifier (e.g., 'cook', 'produce')
    
    Returns:
        File path or None if not found
    """
    if USE_SUPABASE:
        # TODO: Query for specific box type
        pass
    
    try:
        box_files = glob.glob(os.path.join(directory, f"{box_name_slug}_*.json"))
        if not box_files:
            return None
        return max(box_files, key=os.path.getmtime)
    except Exception as e:
        print(f"Error finding box file for {box_name_slug}: {e}")
        return None


def get_latest_comprehensive_file(directory: str = FARM_BOX_DATA_DIR, user_id: str = None) -> Union[str, Dict]:
    """
    Finds the most recent comprehensive scraper results.
    
    LOCAL: Returns file path to latest customize_results_*.json
    PRODUCTION: Returns cart data dict from Supabase
    
    Args:
        directory: Local directory path
        user_id: User identifier for database queries
    
    Returns:
        File path (local) or cart data dict (production)
    """
    if USE_SUPABASE and user_id:
        # TODO: Query Supabase for user's latest comprehensive cart
        # client = get_data_source_client()
        # result = client.table('user_carts')
        #     .select('cart_data')
        #     .eq('user_id', user_id)
        #     .eq('cart_type', 'comprehensive')
        #     .order('created_at', desc=True)
        #     .limit(1)
        #     .execute()
        # return result.data[0]['cart_data'] if result.data else None
        pass
    
    # Local implementation
    try:
        # First try the comprehensive format
        comprehensive_files = glob.glob(os.path.join(directory, "customize_results_*.json"))
        if comprehensive_files:
            return max(comprehensive_files, key=os.path.getmtime)
        
        # Fall back to cart_contents if no comprehensive files
        return get_latest_cart_file(directory)
    except Exception as e:
        print(f"Error finding comprehensive file: {e}")
        return None


def load_cart_data(file_path_or_data: Union[str, Dict]) -> Dict:
    """
    Loads cart data from either a file path or returns the dict directly.
    
    This abstraction allows seamless switching between:
    - LOCAL: File path → read JSON file
    - PRODUCTION: Dict from Supabase → return as-is
    
    Args:
        file_path_or_data: Either a file path string or cart data dict
    
    Returns:
        Cart data dictionary
    """
    if isinstance(file_path_or_data, dict):
        # Already have the data (from Supabase)
        return file_path_or_data
    
    if isinstance(file_path_or_data, str) and os.path.exists(file_path_or_data):
        # Local file path
        try:
            with open(file_path_or_data, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading cart data from {file_path_or_data}: {e}")
            return {}
    
    return {}


def save_analysis_result(analysis_data: Dict, user_id: str = None) -> str:
    """
    Saves analysis results for later retrieval.
    
    LOCAL: Saves to analyses/ directory with UUID
    PRODUCTION: Saves to Supabase cart_analyses table
    
    Args:
        analysis_data: Complete analysis with content, metadata
        user_id: User identifier for database storage
    
    Returns:
        Analysis ID for retrieval
    """
    import uuid
    analysis_id = str(uuid.uuid4())[:8]
    
    if USE_SUPABASE and user_id:
        # TODO: Save to Supabase
        # client = get_data_source_client()
        # result = client.table('cart_analyses').insert({
        #     'id': analysis_id,
        #     'user_id': user_id,
        #     'analysis_content': analysis_data['content'],
        #     'character_count': analysis_data['character_count'],
        #     'created_at': datetime.now().isoformat()
        # }).execute()
        pass
    else:
        # Local file storage
        from pathlib import Path
        analyses_dir = Path("../analyses")
        analyses_dir.mkdir(exist_ok=True)
        
        analysis_file = analyses_dir / f"analysis_{analysis_id}.json"
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_data, f, indent=2, ensure_ascii=False)
        
        print(f"📝 Analysis saved locally: {analysis_file}")
    
    return analysis_id


def get_analysis_by_id(analysis_id: str) -> Optional[Dict]:
    """
    Retrieves a saved analysis by ID.
    
    LOCAL: Reads from analyses/ directory
    PRODUCTION: Queries Supabase cart_analyses table
    
    Args:
        analysis_id: Unique identifier for the analysis
    
    Returns:
        Analysis data dict or None if not found
    """
    if USE_SUPABASE:
        # TODO: Query Supabase
        # client = get_data_source_client()
        # result = client.table('cart_analyses')
        #     .select('*')
        #     .eq('id', analysis_id)
        #     .single()
        #     .execute()
        # return result.data if result.data else None
        pass
    else:
        # Local file retrieval
        from pathlib import Path
        
        # Try different possible paths
        possible_paths = [
            Path(f"../analyses/analysis_{analysis_id}.json"),  # From server directory
            Path(f"analyses/analysis_{analysis_id}.json"),     # From project root
            Path(f"./analyses/analysis_{analysis_id}.json"),   # Current dir
        ]
        
        for analysis_file in possible_paths:
            if analysis_file.exists():
                with open(analysis_file, 'r') as f:
                    return json.load(f)
    
    return None


def get_comprehensive_ingredients_and_data(comprehensive_data: dict) -> Tuple[List[str], dict]:
    """
    Extracts all ingredients from comprehensive scraper data.
    Returns both the ingredient list and structured data for analysis.
    
    This function works with data from either:
    - LOCAL: JSON files from comprehensive_scraper.py
    - PRODUCTION: Cart data stored in Supabase
    
    The data structure is consistent across both sources.
    """
    all_ingredients = []
    analysis_data = {
        'individual_items': [],
        'non_customizable_boxes': [],
        'customizable_boxes': []
    }
    
    # Process individual items (eggs, avocados, etc.)
    for item in comprehensive_data.get('individual_items', []):
        if item.get('selected', True):  # Default to True if not specified
            name = item.get('name', '')
            if name:
                all_ingredients.append(name)
                analysis_data['individual_items'].append(item)
    
    # Process non-customizable boxes (Seasonal Fruit Medley, etc.)
    for box in comprehensive_data.get('non_customizable_boxes', []):
        box_data = {'box_name': box.get('box_name', ''), 'items': []}
        for item in box.get('selected_items', []):
            if item.get('selected', True):
                name = item.get('name', '')
                if name:
                    all_ingredients.append(name)
                    box_data['items'].append(item)
        if box_data['items']:
            analysis_data['non_customizable_boxes'].append(box_data)
    
    # Process customizable boxes (Cook's Box - Paleo with alternatives)
    for box in comprehensive_data.get('customizable_boxes', []):
        box_data = {
            'box_name': box.get('box_name', ''),
            'selected_items': [],
            'available_alternatives': box.get('available_alternatives', [])
        }
        for item in box.get('selected_items', []):
            if item.get('selected', True):
                name = item.get('name', '')
                if name:
                    all_ingredients.append(name)
                    box_data['selected_items'].append(item)
        analysis_data['customizable_boxes'].append(box_data)
    
    return all_ingredients, analysis_data