-- Meal Planning Database Schema for Supabase (FIXED VERSION)
-- Created: 2025-08-31
-- Purpose: Support weekly meal planning with ingredient allocation

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Weekly meal plans (main container)
CREATE TABLE IF NOT EXISTS weekly_meal_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_phone TEXT NOT NULL,
    week_of DATE NOT NULL,
    cart_data JSONB NOT NULL,
    status TEXT DEFAULT 'planning' CHECK (status IN ('planning', 'complete', 'archived')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_user_week UNIQUE(user_phone, week_of)
);

-- Individual meals within a plan
CREATE TABLE IF NOT EXISTS meal_assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meal_plan_id UUID NOT NULL REFERENCES weekly_meal_plans(id) ON DELETE CASCADE,
    day_of_week TEXT NOT NULL CHECK (day_of_week IN ('monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday')),
    meal_data JSONB NOT NULL,
    allocated_ingredients JSONB NOT NULL DEFAULT '[]'::jsonb,
    status TEXT DEFAULT 'assigned' CHECK (status IN ('assigned', 'regenerating', 'locked')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_meal_per_day UNIQUE(meal_plan_id, day_of_week)
);

-- Available ingredient pool tracking
CREATE TABLE IF NOT EXISTS ingredient_pools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meal_plan_id UUID NOT NULL REFERENCES weekly_meal_plans(id) ON DELETE CASCADE,
    ingredient_name TEXT NOT NULL,
    total_quantity DECIMAL(10,3) NOT NULL,
    allocated_quantity DECIMAL(10,3) DEFAULT 0,
    remaining_quantity DECIMAL(10,3) NOT NULL,
    unit TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT unique_ingredient_per_plan UNIQUE(meal_plan_id, ingredient_name),
    CONSTRAINT valid_quantities CHECK (
        total_quantity >= 0 AND 
        allocated_quantity >= 0 AND 
        remaining_quantity >= 0 AND
        allocated_quantity <= total_quantity AND
        remaining_quantity = total_quantity - allocated_quantity
    )
);

-- Session management for cross-device sync
CREATE TABLE IF NOT EXISTS meal_plan_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_phone TEXT NOT NULL,
    session_token TEXT NOT NULL UNIQUE,
    meal_plan_id UUID REFERENCES weekly_meal_plans(id) ON DELETE SET NULL,
    last_active TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '2 hours'),
    device_info JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance (no function predicates)
CREATE INDEX IF NOT EXISTS idx_meal_plans_user_week ON weekly_meal_plans(user_phone, week_of);
CREATE INDEX IF NOT EXISTS idx_meal_plans_status ON weekly_meal_plans(status);
CREATE INDEX IF NOT EXISTS idx_meal_assignments_plan ON meal_assignments(meal_plan_id);
CREATE INDEX IF NOT EXISTS idx_meal_assignments_day ON meal_assignments(meal_plan_id, day_of_week);
CREATE INDEX IF NOT EXISTS idx_ingredient_pools_plan ON ingredient_pools(meal_plan_id);
CREATE INDEX IF NOT EXISTS idx_ingredient_pools_name ON ingredient_pools(meal_plan_id, ingredient_name);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON meal_plan_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON meal_plan_sessions(user_phone);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON meal_plan_sessions(expires_at);

-- Row Level Security (RLS) Policies
ALTER TABLE weekly_meal_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE meal_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE ingredient_pools ENABLE ROW LEVEL SECURITY;
ALTER TABLE meal_plan_sessions ENABLE ROW LEVEL SECURITY;

-- Simple RLS policies (allowing all operations for now - can tighten later)
CREATE POLICY "Allow all operations on meal plans" ON weekly_meal_plans FOR ALL USING (true);
CREATE POLICY "Allow all operations on meal assignments" ON meal_assignments FOR ALL USING (true);
CREATE POLICY "Allow all operations on ingredient pools" ON ingredient_pools FOR ALL USING (true);
CREATE POLICY "Allow all operations on sessions" ON meal_plan_sessions FOR ALL USING (true);

-- Helper function to update ingredient pool quantities
CREATE OR REPLACE FUNCTION update_ingredient_pool_quantities()
RETURNS TRIGGER 
LANGUAGE plpgsql AS $$
BEGIN
    -- Automatically recalculate remaining quantity when allocated quantity changes
    NEW.remaining_quantity = NEW.total_quantity - NEW.allocated_quantity;
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER trigger_update_ingredient_quantities
    BEFORE UPDATE ON ingredient_pools
    FOR EACH ROW
    EXECUTE FUNCTION update_ingredient_pool_quantities();

-- Simple function to clean up expired sessions (no complex loops)
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS INTEGER 
LANGUAGE plpgsql AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM meal_plan_sessions WHERE expires_at < NOW();
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$;

-- Comments for documentation
COMMENT ON TABLE weekly_meal_plans IS 'Main container for weekly meal plans';
COMMENT ON TABLE meal_assignments IS 'Individual meals assigned to specific days';
COMMENT ON TABLE ingredient_pools IS 'Tracks available ingredients and allocations';
COMMENT ON TABLE meal_plan_sessions IS 'Manages user sessions for cross-device sync';
COMMENT ON FUNCTION cleanup_expired_sessions IS 'Removes expired sessions (run via cron)';

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Meal planning schema created successfully!';
    RAISE NOTICE 'Tables: weekly_meal_plans, meal_assignments, ingredient_pools, meal_plan_sessions';
    RAISE NOTICE 'Next step: Use the storage layer in your app to manage meal plans';
END $$;