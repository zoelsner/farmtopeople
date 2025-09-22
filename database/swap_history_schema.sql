-- Swap History Table for Tracking User Cart Changes
-- Prevents ping-pong swap suggestions by remembering recent swaps

CREATE TABLE IF NOT EXISTS swap_history (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    phone VARCHAR(20) NOT NULL,
    delivery_date DATE NOT NULL,
    box_name VARCHAR(100),
    from_item VARCHAR(200) NOT NULL,
    to_item VARCHAR(200) NOT NULL,
    detected_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index for fast lookups by phone and delivery date
CREATE INDEX IF NOT EXISTS idx_swap_history_lookup
ON swap_history(phone, delivery_date DESC, detected_at DESC);

-- Index for phone-only lookups (for user stats)
CREATE INDEX IF NOT EXISTS idx_swap_history_phone
ON swap_history(phone, detected_at DESC);

-- Function to clean up old swap history (older than 30 days)
CREATE OR REPLACE FUNCTION cleanup_old_swaps()
RETURNS void AS $$
BEGIN
    DELETE FROM swap_history
    WHERE detected_at < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;

-- Optional: Set up automated cleanup (uncomment if desired)
-- CREATE EXTENSION IF NOT EXISTS pg_cron;
-- SELECT cron.schedule('cleanup-swaps', '0 2 * * *', 'SELECT cleanup_old_swaps();');

-- Test the table with a sample insert
INSERT INTO swap_history (phone, delivery_date, box_name, from_item, to_item)
VALUES ('+14255551234', '2025-09-18', 'The Cook''s Box - Paleo', 'Organic Lacinato Kale', 'Organically Grown Baby Arugula')
ON CONFLICT DO NOTHING;

-- Verify the table works
SELECT * FROM swap_history WHERE phone = '+14255551234' LIMIT 5;