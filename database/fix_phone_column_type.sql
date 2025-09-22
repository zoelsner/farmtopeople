-- Fix phone column data type in swap_history table
-- Change from VARCHAR(20) to text for consistency with other tables

-- Change phone column from VARCHAR(20) to text
ALTER TABLE swap_history
ALTER COLUMN phone TYPE text;

-- Verify the change worked
SELECT column_name, data_type, character_maximum_length
FROM information_schema.columns
WHERE table_name = 'swap_history'
AND column_name = 'phone';

-- Should show:
-- column_name | data_type | character_maximum_length
-- phone       | text      | null

COMMENT ON COLUMN swap_history.phone IS 'User phone number - changed to text type for consistency with other tables';