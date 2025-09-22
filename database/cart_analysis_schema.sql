-- Cart Analysis Persistence Schema for Supabase
-- Created: 2025-09-18
-- Purpose: Store cart analyses to prevent data loss after Redis TTL expires

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Cart analyses table (stores the GPT-generated meal suggestions and add-ons)
CREATE TABLE IF NOT EXISTS cart_analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_phone TEXT NOT NULL,
    analysis_date DATE NOT NULL,
    cart_data JSONB NOT NULL,  -- The raw cart data from scraper
    meal_suggestions JSONB NOT NULL,  -- The 5 GPT-generated meal suggestions
    add_ons JSONB NOT NULL DEFAULT '[]'::jsonb,  -- The meal-aware add-on suggestions
    swaps JSONB NOT NULL DEFAULT '[]'::jsonb,  -- Category-aware swap suggestions
    delivery_date TEXT,  -- The delivery date extracted from cart
    analysis_metadata JSONB DEFAULT '{}'::jsonb,  -- Additional metadata (GPT model used, processing time, etc.)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT (NOW() + INTERVAL '7 days'),  -- Auto-cleanup after 7 days

    -- Indexes for efficient querying
    CONSTRAINT unique_user_analysis_per_day UNIQUE(user_phone, analysis_date)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_cart_analyses_user_phone ON cart_analyses(user_phone);
CREATE INDEX IF NOT EXISTS idx_cart_analyses_analysis_date ON cart_analyses(analysis_date);
CREATE INDEX IF NOT EXISTS idx_cart_analyses_expires_at ON cart_analyses(expires_at);

-- Meal locks table (stores which meals users have locked/liked)
CREATE TABLE IF NOT EXISTS meal_locks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    analysis_id UUID NOT NULL REFERENCES cart_analyses(id) ON DELETE CASCADE,
    meal_index INTEGER NOT NULL CHECK (meal_index >= 0 AND meal_index <= 4),  -- 0-4 for 5 meals
    is_locked BOOLEAN DEFAULT false,
    locked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_lock_per_meal UNIQUE(analysis_id, meal_index)
);

-- Create a function to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers to auto-update the updated_at column
CREATE TRIGGER update_cart_analyses_updated_at
    BEFORE UPDATE ON cart_analyses
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_meal_locks_updated_at
    BEFORE UPDATE ON meal_locks
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Create a function to clean up expired analyses
CREATE OR REPLACE FUNCTION cleanup_expired_analyses()
RETURNS void AS $$
BEGIN
    DELETE FROM cart_analyses WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql;

-- Example: Schedule cleanup (run manually or via cron)
-- SELECT cleanup_expired_analyses();