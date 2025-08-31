-- Add meal_suggestions column to latest_cart_data table
-- Created: 2025-08-31
-- Purpose: Store generated meal suggestions to maintain consistency between cart analysis and meal calendar

-- Add the meal_suggestions column to store AI-generated meal plans
ALTER TABLE latest_cart_data 
ADD COLUMN IF NOT EXISTS meal_suggestions JSONB DEFAULT '[]'::jsonb;

-- Add an index for faster queries on meal suggestions
CREATE INDEX IF NOT EXISTS idx_latest_cart_meal_suggestions 
ON latest_cart_data USING GIN (meal_suggestions);

-- Add a comment for documentation
COMMENT ON COLUMN latest_cart_data.meal_suggestions IS 'AI-generated meal suggestions from cart analysis, used to populate initial meal calendar';

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'meal_suggestions column added to latest_cart_data table successfully!';
    RAISE NOTICE 'This column will store meal suggestions to maintain consistency between cart view and meal calendar';
END $$;