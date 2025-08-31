"""
Abstract base class for meal plan storage.
This abstraction allows easy swapping between Supabase and Redis implementations.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Tuple
from datetime import datetime, date


class MealPlanStorage(ABC):
    """Abstract base class for meal plan storage implementations."""
    
    @abstractmethod
    async def create_meal_plan(self, user_phone: str, week_of: date, cart_data: Dict) -> str:
        """
        Create a new meal plan for the specified week.
        
        Args:
            user_phone: User's phone number (identifier)
            week_of: Date of the week (typically Monday)
            cart_data: Complete cart data from scraper
            
        Returns:
            meal_plan_id: UUID of created meal plan
        """
        pass
    
    @abstractmethod
    async def get_meal_plan(self, user_phone: str, week_of: date) -> Optional[Dict]:
        """
        Retrieve a meal plan for the specified week.
        
        Args:
            user_phone: User's phone number
            week_of: Date of the week
            
        Returns:
            Complete meal plan data or None if not found
        """
        pass
    
    @abstractmethod
    async def update_meal_plan_status(self, plan_id: str, status: str) -> bool:
        """Update meal plan status (planning, complete, archived)."""
        pass
    
    @abstractmethod
    async def assign_meal(self, plan_id: str, day: str, meal_data: Dict, ingredients: List[Dict]) -> bool:
        """
        Assign a meal to a specific day.
        
        Args:
            plan_id: Meal plan UUID
            day: Day of week (monday, tuesday, etc.)
            meal_data: Complete meal information
            ingredients: List of ingredients to allocate
            
        Returns:
            Success status
        """
        pass
    
    @abstractmethod
    async def get_meal_assignment(self, plan_id: str, day: str) -> Optional[Dict]:
        """Get meal assignment for a specific day."""
        pass
    
    @abstractmethod
    async def remove_meal_assignment(self, plan_id: str, day: str) -> bool:
        """Remove meal assignment and release ingredients."""
        pass
    
    @abstractmethod
    async def get_all_meals(self, plan_id: str) -> Dict[str, Dict]:
        """Get all meal assignments for a plan."""
        pass
    
    @abstractmethod
    async def get_ingredient_pool(self, plan_id: str) -> Dict[str, Dict]:
        """
        Get current ingredient availability.
        
        Returns:
            Dict mapping ingredient names to availability info:
            {
                "Chicken Breast": {
                    "total": 1.5,
                    "allocated": 0.5,
                    "remaining": 1.0,
                    "unit": "lb"
                }
            }
        """
        pass
    
    @abstractmethod
    async def allocate_ingredients(self, plan_id: str, day: str, ingredients: List[Dict]) -> Dict:
        """
        Allocate ingredients for a meal.
        
        Args:
            plan_id: Meal plan UUID
            day: Day of week
            ingredients: List of ingredients to allocate
                [{"name": "Chicken Breast", "quantity": 0.5, "unit": "lb"}]
                
        Returns:
            Result dict with success status and any conflicts
        """
        pass
    
    @abstractmethod
    async def release_ingredients(self, plan_id: str, day: str) -> bool:
        """Release ingredients back to pool when meal is removed."""
        pass
    
    @abstractmethod
    async def check_ingredient_conflicts(self, plan_id: str, ingredients: List[Dict]) -> List[Dict]:
        """
        Check if requested ingredients are available.
        
        Returns:
            List of conflicts with suggested resolutions
        """
        pass
    
    @abstractmethod
    async def create_session(self, user_phone: str, device_info: Dict = None) -> str:
        """
        Create a new user session for cross-device sync.
        
        Returns:
            session_token: Unique session identifier
        """
        pass
    
    @abstractmethod
    async def validate_session(self, session_token: str) -> Optional[Dict]:
        """
        Validate session token and return session info.
        
        Returns:
            Session data or None if invalid/expired
        """
        pass
    
    @abstractmethod
    async def update_session_activity(self, session_token: str) -> bool:
        """Update last_active timestamp for session."""
        pass
    
    @abstractmethod
    async def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions. Returns number of sessions cleaned up."""
        pass


class StorageError(Exception):
    """Base exception for storage operations."""
    pass


class ConflictError(StorageError):
    """Raised when ingredient allocation conflicts occur."""
    def __init__(self, conflicts: List[Dict]):
        self.conflicts = conflicts
        super().__init__(f"Ingredient conflicts: {conflicts}")


class NotFoundError(StorageError):
    """Raised when requested resource is not found."""
    pass


class ValidationError(StorageError):
    """Raised when data validation fails."""
    pass