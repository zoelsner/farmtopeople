"""
Supabase implementation of meal plan storage.
Provides persistent storage with real-time sync capabilities.
"""

import json
import uuid
import logging
from typing import Dict, List, Optional
from datetime import datetime, date, timedelta
from decimal import Decimal

from .base import MealPlanStorage, StorageError, ConflictError, NotFoundError, ValidationError
import supabase_client as db

logger = logging.getLogger(__name__)


class SupabaseMealStorage(MealPlanStorage):
    """Supabase implementation of meal plan storage."""
    
    def __init__(self):
        self.client = db.get_client()
    
    def _initialize_ingredient_pool(self, plan_id: str, cart_data: Dict):
        """Initialize ingredient pool from cart data."""
        ingredients_to_insert = []
        
        # Process individual items
        for item in cart_data.get('individual_items', []):
            ingredients_to_insert.append({
                'meal_plan_id': plan_id,
                'ingredient_name': item.get('name', 'Unknown'),
                'total_quantity': float(item.get('quantity', 1)),
                'allocated_quantity': 0,
                'remaining_quantity': float(item.get('quantity', 1)),
                'unit': item.get('unit', 'piece')
            })
        
        # Process customizable boxes
        for box in cart_data.get('customizable_boxes', []):
            for item in box.get('selected_items', []):
                ingredients_to_insert.append({
                    'meal_plan_id': plan_id,
                    'ingredient_name': item.get('name', 'Unknown'),
                    'total_quantity': float(item.get('quantity', 1)),
                    'allocated_quantity': 0,
                    'remaining_quantity': float(item.get('quantity', 1)),
                    'unit': item.get('unit', 'piece')
                })
        
        # Process non-customizable boxes
        for box in cart_data.get('non_customizable_boxes', []):
            for item in box.get('selected_items', []):
                ingredients_to_insert.append({
                    'meal_plan_id': plan_id,
                    'ingredient_name': item.get('name', 'Unknown'),
                    'total_quantity': float(item.get('quantity', 1)),
                    'allocated_quantity': 0,
                    'remaining_quantity': float(item.get('quantity', 1)),
                    'unit': item.get('unit', 'piece')
                })
        
        # Insert all ingredients
        if ingredients_to_insert:
            self.client.table('ingredient_pools').insert(ingredients_to_insert).execute()
    
    async def create_meal_plan(self, user_phone: str, week_of: date, cart_data: Dict) -> str:
        """Create a new meal plan and initialize ingredient pool."""
        try:
            # Create meal plan record
            meal_plan_data = {
                'user_phone': user_phone,
                'week_of': week_of.isoformat(),
                'cart_data': cart_data,
                'status': 'planning'
            }
            
            result = self.client.table('weekly_meal_plans').insert(meal_plan_data).execute()
            
            if not result.data:
                raise StorageError("Failed to create meal plan")
            
            plan_id = result.data[0]['id']
            
            # Initialize ingredient pool directly in Python
            self._initialize_ingredient_pool(plan_id, cart_data)
            
            logger.info(f"Created meal plan {plan_id} for user {user_phone}, week {week_of}")
            return plan_id
            
        except Exception as e:
            logger.error(f"Error creating meal plan: {e}")
            raise StorageError(f"Failed to create meal plan: {e}")
    
    async def get_meal_plan(self, user_phone: str, week_of: date) -> Optional[Dict]:
        """Retrieve complete meal plan with all meals and ingredient status."""
        try:
            # Get base meal plan
            plan_result = self.client.table('weekly_meal_plans').select('*').eq('user_phone', user_phone).eq('week_of', week_of.isoformat()).execute()
            
            if not plan_result.data:
                return None
            
            meal_plan = plan_result.data[0]
            plan_id = meal_plan['id']
            
            # Get all meal assignments
            meals_result = self.client.table('meal_assignments').select('*').eq('meal_plan_id', plan_id).execute()
            
            meals = {}
            for meal in meals_result.data:
                meals[meal['day_of_week']] = {
                    'id': meal['id'],
                    'meal_data': meal['meal_data'],
                    'allocated_ingredients': meal['allocated_ingredients'],
                    'status': meal['status']
                }
            
            # Get ingredient pool
            ingredient_pool = await self.get_ingredient_pool(plan_id)
            
            return {
                'id': plan_id,
                'user_phone': meal_plan['user_phone'],
                'week_of': meal_plan['week_of'],
                'cart_data': meal_plan['cart_data'],
                'status': meal_plan['status'],
                'meals': meals,
                'ingredient_pool': ingredient_pool,
                'created_at': meal_plan['created_at'],
                'updated_at': meal_plan['updated_at']
            }
            
        except Exception as e:
            logger.error(f"Error getting meal plan: {e}")
            raise StorageError(f"Failed to get meal plan: {e}")
    
    async def update_meal_plan_status(self, plan_id: str, status: str) -> bool:
        """Update meal plan status."""
        try:
            valid_statuses = ['planning', 'complete', 'archived']
            if status not in valid_statuses:
                raise ValidationError(f"Invalid status: {status}")
            
            result = self.client.table('weekly_meal_plans').update({
                'status': status,
                'updated_at': datetime.now().isoformat()
            }).eq('id', plan_id).execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error updating meal plan status: {e}")
            raise StorageError(f"Failed to update status: {e}")
    
    async def assign_meal(self, plan_id: str, day: str, meal_data: Dict, ingredients: List[Dict]) -> bool:
        """Assign meal to day with ingredient allocation."""
        try:
            # First check for conflicts
            conflicts = await self.check_ingredient_conflicts(plan_id, ingredients)
            if conflicts:
                raise ConflictError(conflicts)
            
            # Start transaction-like behavior
            # 1. Remove existing meal assignment (if any) and release ingredients
            await self.remove_meal_assignment(plan_id, day)
            
            # 2. Allocate new ingredients
            allocation_result = await self.allocate_ingredients(plan_id, day, ingredients)
            if not allocation_result.get('success'):
                raise ConflictError(allocation_result.get('conflicts', []))
            
            # 3. Create meal assignment
            meal_assignment = {
                'meal_plan_id': plan_id,
                'day_of_week': day,
                'meal_data': meal_data,
                'allocated_ingredients': ingredients,
                'status': 'assigned'
            }
            
            result = self.client.table('meal_assignments').upsert(meal_assignment).execute()
            
            if not result.data:
                # Rollback: release the ingredients we just allocated
                await self.release_ingredients(plan_id, day)
                raise StorageError("Failed to create meal assignment")
            
            # 4. Update meal plan timestamp
            self.client.table('weekly_meal_plans').update({
                'updated_at': datetime.now().isoformat()
            }).eq('id', plan_id).execute()
            
            logger.info(f"Assigned meal to {day} in plan {plan_id}")
            return True
            
        except ConflictError:
            raise  # Re-raise conflict errors as-is
        except Exception as e:
            logger.error(f"Error assigning meal: {e}")
            raise StorageError(f"Failed to assign meal: {e}")
    
    async def get_meal_assignment(self, plan_id: str, day: str) -> Optional[Dict]:
        """Get meal assignment for specific day."""
        try:
            result = self.client.table('meal_assignments').select('*').eq('meal_plan_id', plan_id).eq('day_of_week', day).execute()
            
            if not result.data:
                return None
                
            meal = result.data[0]
            return {
                'id': meal['id'],
                'meal_data': meal['meal_data'],
                'allocated_ingredients': meal['allocated_ingredients'],
                'status': meal['status']
            }
            
        except Exception as e:
            logger.error(f"Error getting meal assignment: {e}")
            raise StorageError(f"Failed to get meal assignment: {e}")
    
    async def remove_meal_assignment(self, plan_id: str, day: str) -> bool:
        """Remove meal assignment and release ingredients."""
        try:
            # First release ingredients
            await self.release_ingredients(plan_id, day)
            
            # Then remove meal assignment
            result = self.client.table('meal_assignments').delete().eq('meal_plan_id', plan_id).eq('day_of_week', day).execute()
            
            logger.info(f"Removed meal assignment for {day} in plan {plan_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error removing meal assignment: {e}")
            raise StorageError(f"Failed to remove meal assignment: {e}")
    
    async def get_all_meals(self, plan_id: str) -> Dict[str, Dict]:
        """Get all meal assignments for a plan."""
        try:
            result = self.client.table('meal_assignments').select('*').eq('meal_plan_id', plan_id).execute()
            
            meals = {}
            for meal in result.data:
                meals[meal['day_of_week']] = {
                    'id': meal['id'],
                    'meal_data': meal['meal_data'],
                    'allocated_ingredients': meal['allocated_ingredients'],
                    'status': meal['status']
                }
            
            return meals
            
        except Exception as e:
            logger.error(f"Error getting all meals: {e}")
            raise StorageError(f"Failed to get all meals: {e}")
    
    async def get_ingredient_pool(self, plan_id: str) -> Dict[str, Dict]:
        """Get current ingredient pool status."""
        try:
            result = self.client.table('ingredient_pools').select('*').eq('meal_plan_id', plan_id).execute()
            
            ingredient_pool = {}
            for ingredient in result.data:
                ingredient_pool[ingredient['ingredient_name']] = {
                    'total': float(ingredient['total_quantity']),
                    'allocated': float(ingredient['allocated_quantity']),
                    'remaining': float(ingredient['remaining_quantity']),
                    'unit': ingredient['unit']
                }
            
            return ingredient_pool
            
        except Exception as e:
            logger.error(f"Error getting ingredient pool: {e}")
            raise StorageError(f"Failed to get ingredient pool: {e}")
    
    async def allocate_ingredients(self, plan_id: str, day: str, ingredients: List[Dict]) -> Dict:
        """Allocate ingredients for a meal."""
        try:
            conflicts = []
            
            for ingredient in ingredients:
                name = ingredient['name']
                quantity = Decimal(str(ingredient['quantity']))
                
                # Get current ingredient status
                result = self.client.table('ingredient_pools').select('*').eq('meal_plan_id', plan_id).eq('ingredient_name', name).execute()
                
                if not result.data:
                    conflicts.append({
                        'ingredient': name,
                        'issue': 'not_available',
                        'message': f"Ingredient '{name}' not found in cart"
                    })
                    continue
                
                current = result.data[0]
                remaining = Decimal(str(current['remaining_quantity']))
                
                if quantity > remaining:
                    conflicts.append({
                        'ingredient': name,
                        'requested': float(quantity),
                        'available': float(remaining),
                        'unit': current['unit'],
                        'issue': 'insufficient_quantity',
                        'suggestion': f"Reduce to {remaining} {current['unit']} or less"
                    })
                    continue
                
                # Allocate the ingredient
                new_allocated = Decimal(str(current['allocated_quantity'])) + quantity
                new_remaining = Decimal(str(current['total_quantity'])) - new_allocated
                
                self.client.table('ingredient_pools').update({
                    'allocated_quantity': float(new_allocated),
                    'remaining_quantity': float(new_remaining),
                    'updated_at': datetime.now().isoformat()
                }).eq('id', current['id']).execute()
            
            if conflicts:
                return {'success': False, 'conflicts': conflicts}
            
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Error allocating ingredients: {e}")
            raise StorageError(f"Failed to allocate ingredients: {e}")
    
    async def release_ingredients(self, plan_id: str, day: str) -> bool:
        """Release ingredients back to pool when meal is removed."""
        try:
            # Get current meal assignment to see what ingredients to release
            meal = await self.get_meal_assignment(plan_id, day)
            if not meal or not meal.get('allocated_ingredients'):
                return True  # Nothing to release
            
            for ingredient in meal['allocated_ingredients']:
                name = ingredient['name']
                quantity = Decimal(str(ingredient['quantity']))
                
                # Get current ingredient status
                result = self.client.table('ingredient_pools').select('*').eq('meal_plan_id', plan_id).eq('ingredient_name', name).execute()
                
                if result.data:
                    current = result.data[0]
                    new_allocated = max(Decimal('0'), Decimal(str(current['allocated_quantity'])) - quantity)
                    new_remaining = Decimal(str(current['total_quantity'])) - new_allocated
                    
                    self.client.table('ingredient_pools').update({
                        'allocated_quantity': float(new_allocated),
                        'remaining_quantity': float(new_remaining),
                        'updated_at': datetime.now().isoformat()
                    }).eq('id', current['id']).execute()
            
            logger.info(f"Released ingredients for {day} in plan {plan_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error releasing ingredients: {e}")
            raise StorageError(f"Failed to release ingredients: {e}")
    
    async def check_ingredient_conflicts(self, plan_id: str, ingredients: List[Dict]) -> List[Dict]:
        """Check for ingredient allocation conflicts."""
        try:
            conflicts = []
            
            for ingredient in ingredients:
                name = ingredient['name']
                quantity = Decimal(str(ingredient['quantity']))
                
                result = self.client.table('ingredient_pools').select('*').eq('meal_plan_id', plan_id).eq('ingredient_name', name).execute()
                
                if not result.data:
                    conflicts.append({
                        'ingredient': name,
                        'issue': 'not_available',
                        'message': f"Ingredient '{name}' not found in cart"
                    })
                    continue
                
                current = result.data[0]
                remaining = Decimal(str(current['remaining_quantity']))
                
                if quantity > remaining:
                    conflicts.append({
                        'ingredient': name,
                        'requested': float(quantity),
                        'available': float(remaining),
                        'unit': current['unit'],
                        'issue': 'insufficient_quantity'
                    })
            
            return conflicts
            
        except Exception as e:
            logger.error(f"Error checking conflicts: {e}")
            raise StorageError(f"Failed to check conflicts: {e}")
    
    async def create_session(self, user_phone: str, device_info: Dict = None) -> str:
        """Create new session for cross-device sync."""
        try:
            session_token = str(uuid.uuid4())
            expires_at = datetime.now() + timedelta(hours=2)
            
            session_data = {
                'user_phone': user_phone,
                'session_token': session_token,
                'expires_at': expires_at.isoformat(),
                'device_info': device_info or {}
            }
            
            result = self.client.table('meal_plan_sessions').insert(session_data).execute()
            
            if not result.data:
                raise StorageError("Failed to create session")
            
            logger.info(f"Created session {session_token} for user {user_phone}")
            return session_token
            
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            raise StorageError(f"Failed to create session: {e}")
    
    async def validate_session(self, session_token: str) -> Optional[Dict]:
        """Validate session and return session info."""
        try:
            result = self.client.table('meal_plan_sessions').select('*').eq('session_token', session_token).gte('expires_at', datetime.now().isoformat()).execute()
            
            if not result.data:
                return None
                
            session = result.data[0]
            return {
                'user_phone': session['user_phone'],
                'session_token': session['session_token'],
                'meal_plan_id': session.get('meal_plan_id'),
                'device_info': session.get('device_info', {}),
                'expires_at': session['expires_at']
            }
            
        except Exception as e:
            logger.error(f"Error validating session: {e}")
            return None
    
    async def update_session_activity(self, session_token: str) -> bool:
        """Update session last activity timestamp."""
        try:
            result = self.client.table('meal_plan_sessions').update({
                'last_active': datetime.now().isoformat()
            }).eq('session_token', session_token).execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error updating session activity: {e}")
            return False
    
    async def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions."""
        try:
            result = self.client.rpc('cleanup_expired_sessions').execute()
            count = result.data if result.data else 0
            logger.info(f"Cleaned up {count} expired sessions")
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning up sessions: {e}")
            return 0