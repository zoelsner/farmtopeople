-- Meal Planning Database Schema for Supabase
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

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_meal_plans_user_week ON weekly_meal_plans(user_phone, week_of);
CREATE INDEX IF NOT EXISTS idx_meal_plans_status ON weekly_meal_plans(status);
CREATE INDEX IF NOT EXISTS idx_meal_assignments_plan ON meal_assignments(meal_plan_id);
CREATE INDEX IF NOT EXISTS idx_meal_assignments_day ON meal_assignments(meal_plan_id, day_of_week);
CREATE INDEX IF NOT EXISTS idx_ingredient_pools_plan ON ingredient_pools(meal_plan_id);
CREATE INDEX IF NOT EXISTS idx_ingredient_pools_name ON ingredient_pools(meal_plan_id, ingredient_name);
CREATE INDEX IF NOT EXISTS idx_sessions_token ON meal_plan_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON meal_plan_sessions(user_phone);
CREATE INDEX IF NOT EXISTS idx_sessions_active ON meal_plan_sessions(expires_at) WHERE expires_at > NOW();

-- Row Level Security (RLS) Policies
ALTER TABLE weekly_meal_plans ENABLE ROW LEVEL SECURITY;
ALTER TABLE meal_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE ingredient_pools ENABLE ROW LEVEL SECURITY;
ALTER TABLE meal_plan_sessions ENABLE ROW LEVEL SECURITY;

-- RLS Policies for weekly_meal_plans
CREATE POLICY "Users can view their own meal plans" ON weekly_meal_plans
    FOR SELECT USING (user_phone = current_user OR user_phone = (current_setting('request.jwt.claims', true)::json->>'phone'));

CREATE POLICY "Users can create their own meal plans" ON weekly_meal_plans
    FOR INSERT WITH CHECK (user_phone = current_user OR user_phone = (current_setting('request.jwt.claims', true)::json->>'phone'));

CREATE POLICY "Users can update their own meal plans" ON weekly_meal_plans
    FOR UPDATE USING (user_phone = current_user OR user_phone = (current_setting('request.jwt.claims', true)::json->>'phone'));

CREATE POLICY "Users can delete their own meal plans" ON weekly_meal_plans
    FOR DELETE USING (user_phone = current_user OR user_phone = (current_setting('request.jwt.claims', true)::json->>'phone'));

-- RLS Policies for meal_assignments (inherit from parent meal plan)
CREATE POLICY "Users can view meals from their plans" ON meal_assignments
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM weekly_meal_plans wmp 
            WHERE wmp.id = meal_assignments.meal_plan_id 
            AND (wmp.user_phone = current_user OR wmp.user_phone = (current_setting('request.jwt.claims', true)::json->>'phone'))
        )
    );

CREATE POLICY "Users can manage meals from their plans" ON meal_assignments
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM weekly_meal_plans wmp 
            WHERE wmp.id = meal_assignments.meal_plan_id 
            AND (wmp.user_phone = current_user OR wmp.user_phone = (current_setting('request.jwt.claims', true)::json->>'phone'))
        )
    );

-- RLS Policies for ingredient_pools (inherit from parent meal plan)
CREATE POLICY "Users can view ingredients from their plans" ON ingredient_pools
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM weekly_meal_plans wmp 
            WHERE wmp.id = ingredient_pools.meal_plan_id 
            AND (wmp.user_phone = current_user OR wmp.user_phone = (current_setting('request.jwt.claims', true)::json->>'phone'))
        )
    );

CREATE POLICY "Users can manage ingredients from their plans" ON ingredient_pools
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM weekly_meal_plans wmp 
            WHERE wmp.id = ingredient_pools.meal_plan_id 
            AND (wmp.user_phone = current_user OR wmp.user_phone = (current_setting('request.jwt.claims', true)::json->>'phone'))
        )
    );

-- RLS Policies for sessions
CREATE POLICY "Users can view their own sessions" ON meal_plan_sessions
    FOR SELECT USING (user_phone = current_user OR user_phone = (current_setting('request.jwt.claims', true)::json->>'phone'));

CREATE POLICY "Users can create their own sessions" ON meal_plan_sessions
    FOR INSERT WITH CHECK (user_phone = current_user OR user_phone = (current_setting('request.jwt.claims', true)::json->>'phone'));

-- Helper functions for ingredient management
CREATE OR REPLACE FUNCTION update_ingredient_pool_quantities()
RETURNS TRIGGER AS $$
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

-- Function to initialize ingredient pool from cart data
CREATE OR REPLACE FUNCTION initialize_ingredient_pool(plan_id UUID, cart_data JSONB)
RETURNS VOID 
LANGUAGE plpgsql
SECURITY DEFINER AS $$
DECLARE
    item JSONB;
    box JSONB;
    box_item JSONB;
BEGIN
    -- Clear existing ingredients for this plan
    DELETE FROM ingredient_pools WHERE meal_plan_id = plan_id;
    
    -- Process individual items
    IF cart_data ? 'individual_items' THEN
        FOR item IN SELECT * FROM jsonb_array_elements(cart_data->'individual_items')
        LOOP
            INSERT INTO ingredient_pools (meal_plan_id, ingredient_name, total_quantity, remaining_quantity, unit)
            VALUES (
                plan_id,
                item->>'name',
                COALESCE((item->>'quantity')::decimal, 1),
                COALESCE((item->>'quantity')::decimal, 1),
                COALESCE(item->>'unit', 'piece')
            )
            ON CONFLICT (meal_plan_id, ingredient_name) DO UPDATE SET
                total_quantity = ingredient_pools.total_quantity + EXCLUDED.total_quantity,
                remaining_quantity = ingredient_pools.remaining_quantity + EXCLUDED.total_quantity;
        END LOOP;
    END IF;
    
    -- Process customizable boxes
    IF cart_data ? 'customizable_boxes' THEN
        FOR box IN SELECT * FROM jsonb_array_elements(cart_data->'customizable_boxes')
        LOOP
            IF box ? 'selected_items' THEN
                FOR box_item IN SELECT * FROM jsonb_array_elements(box->'selected_items')
                LOOP
                    INSERT INTO ingredient_pools (meal_plan_id, ingredient_name, total_quantity, remaining_quantity, unit)
                    VALUES (
                        plan_id,
                        box_item->>'name',
                        COALESCE((box_item->>'quantity')::decimal, 1),
                        COALESCE((box_item->>'quantity')::decimal, 1),
                        COALESCE(box_item->>'unit', 'piece')
                    )
                    ON CONFLICT (meal_plan_id, ingredient_name) DO UPDATE SET
                        total_quantity = ingredient_pools.total_quantity + EXCLUDED.total_quantity,
                        remaining_quantity = ingredient_pools.remaining_quantity + EXCLUDED.total_quantity;
                END LOOP;
            END IF;
        END LOOP;
    END IF;
    
    -- Process non-customizable boxes
    IF cart_data ? 'non_customizable_boxes' THEN
        FOR box IN SELECT * FROM jsonb_array_elements(cart_data->'non_customizable_boxes')
        LOOP
            IF box ? 'selected_items' THEN
                FOR box_item IN SELECT * FROM jsonb_array_elements(box->'selected_items')
                LOOP
                    INSERT INTO ingredient_pools (meal_plan_id, ingredient_name, total_quantity, remaining_quantity, unit)
                    VALUES (
                        plan_id,
                        box_item->>'name',
                        COALESCE((box_item->>'quantity')::decimal, 1),
                        COALESCE((box_item->>'quantity')::decimal, 1),
                        COALESCE(box_item->>'unit', 'piece')
                    )
                    ON CONFLICT (meal_plan_id, ingredient_name) DO UPDATE SET
                        total_quantity = ingredient_pools.total_quantity + EXCLUDED.total_quantity,
                        remaining_quantity = ingredient_pools.remaining_quantity + EXCLUDED.total_quantity;
                END LOOP;
            END IF;
        END LOOP;
    END IF;
END;
$$;

-- Function to clean up expired sessions
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS INTEGER 
LANGUAGE plpgsql
SECURITY DEFINER AS $$
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
COMMENT ON FUNCTION initialize_ingredient_pool IS 'Populates ingredient pool from cart data';
COMMENT ON FUNCTION cleanup_expired_sessions IS 'Removes expired sessions (run via cron)';