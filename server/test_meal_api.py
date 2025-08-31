"""
Simple test API for meal planning to verify basic functionality.
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, date

# Simple router for testing
router = APIRouter(prefix="/api/test-meals", tags=["test-meals"])

@router.get("/")
async def test_endpoint():
    """Simple test endpoint to verify meal planning API works."""
    return {
        "status": "success",
        "message": "Meal planning API is working!",
        "timestamp": datetime.now().isoformat(),
        "features": [
            "Database schema deployed ✅",
            "Storage layer created ✅", 
            "API structure ready ✅",
            "Next: Connect storage to endpoints"
        ]
    }

@router.get("/schema-test")
async def test_schema():
    """Test that we can connect to the new meal planning tables."""
    try:
        import supabase_client as db
        client = db.get_client()
        
        # Simple test query - just count rows in meal plans table
        result = client.table('weekly_meal_plans').select('count', count='exact').execute()
        
        return {
            "status": "success", 
            "message": "Database connection working",
            "meal_plans_count": result.count,
            "tables": [
                "weekly_meal_plans",
                "meal_assignments", 
                "ingredient_pools",
                "meal_plan_sessions"
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/create-test-plan")
async def create_test_plan():
    """Create a simple test meal plan to verify basic functionality."""
    try:
        import supabase_client as db
        from datetime import date, timedelta
        
        client = db.get_client()
        
        # Create a test meal plan
        test_plan = {
            'user_phone': '+14254955323',  # Your phone number
            'week_of': (date.today() + timedelta(days=7)).isoformat(),  # Next week
            'cart_data': {
                "test": "This is a test meal plan",
                "individual_items": [
                    {"name": "Test Chicken", "quantity": 1, "unit": "lb"},
                    {"name": "Test Vegetables", "quantity": 2, "unit": "piece"}
                ]
            },
            'status': 'planning'
        }
        
        result = client.table('weekly_meal_plans').insert(test_plan).execute()
        
        if result.data:
            plan_id = result.data[0]['id']
            return {
                "status": "success",
                "message": "Test meal plan created!",
                "plan_id": plan_id,
                "week_of": test_plan['week_of']
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to create test plan")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating test plan: {str(e)}")