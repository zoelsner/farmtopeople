-- Function to initialize ingredient pool from cart data
-- Created: 2025-08-31
-- Purpose: Parse cart data and populate ingredient_pools table

CREATE OR REPLACE FUNCTION initialize_ingredient_pool(p_plan_id UUID, p_cart_data JSONB)
RETURNS VOID 
LANGUAGE plpgsql AS $$
DECLARE
    item JSONB;
    ingredient_name TEXT;
    ingredient_quantity DECIMAL;
    ingredient_unit TEXT;
BEGIN
    -- Process individual items
    IF p_cart_data ? 'individual_items' THEN
        FOR item IN SELECT * FROM jsonb_array_elements(p_cart_data->'individual_items')
        LOOP
            ingredient_name := item->>'name';
            ingredient_quantity := COALESCE((item->>'quantity')::DECIMAL, 1);
            ingredient_unit := COALESCE(item->>'unit', 'piece');
            
            -- Insert into ingredient pool
            INSERT INTO ingredient_pools (
                meal_plan_id,
                ingredient_name,
                total_quantity,
                allocated_quantity,
                remaining_quantity,
                unit
            ) VALUES (
                p_plan_id,
                ingredient_name,
                ingredient_quantity,
                0,
                ingredient_quantity,
                ingredient_unit
            ) ON CONFLICT (meal_plan_id, ingredient_name) DO UPDATE
            SET 
                total_quantity = ingredient_pools.total_quantity + EXCLUDED.total_quantity,
                remaining_quantity = ingredient_pools.remaining_quantity + EXCLUDED.total_quantity;
        END LOOP;
    END IF;
    
    -- Process customizable boxes
    IF p_cart_data ? 'customizable_boxes' THEN
        FOR item IN SELECT * FROM jsonb_array_elements(p_cart_data->'customizable_boxes')
        LOOP
            -- Process selected items in each box
            IF item ? 'selected_items' THEN
                FOR item IN SELECT * FROM jsonb_array_elements(item->'selected_items')
                LOOP
                    ingredient_name := item->>'name';
                    ingredient_quantity := COALESCE((item->>'quantity')::DECIMAL, 1);
                    ingredient_unit := COALESCE(item->>'unit', 'piece');
                    
                    INSERT INTO ingredient_pools (
                        meal_plan_id,
                        ingredient_name,
                        total_quantity,
                        allocated_quantity,
                        remaining_quantity,
                        unit
                    ) VALUES (
                        p_plan_id,
                        ingredient_name,
                        ingredient_quantity,
                        0,
                        ingredient_quantity,
                        ingredient_unit
                    ) ON CONFLICT (meal_plan_id, ingredient_name) DO UPDATE
                    SET 
                        total_quantity = ingredient_pools.total_quantity + EXCLUDED.total_quantity,
                        remaining_quantity = ingredient_pools.remaining_quantity + EXCLUDED.total_quantity;
                END LOOP;
            END IF;
        END LOOP;
    END IF;
    
    -- Process non-customizable boxes
    IF p_cart_data ? 'non_customizable_boxes' THEN
        FOR item IN SELECT * FROM jsonb_array_elements(p_cart_data->'non_customizable_boxes')
        LOOP
            -- Process selected items in each box
            IF item ? 'selected_items' THEN
                FOR item IN SELECT * FROM jsonb_array_elements(item->'selected_items')
                LOOP
                    ingredient_name := item->>'name';
                    ingredient_quantity := COALESCE((item->>'quantity')::DECIMAL, 1);
                    ingredient_unit := COALESCE(item->>'unit', 'piece');
                    
                    INSERT INTO ingredient_pools (
                        meal_plan_id,
                        ingredient_name,
                        total_quantity,
                        allocated_quantity,
                        remaining_quantity,
                        unit
                    ) VALUES (
                        p_plan_id,
                        ingredient_name,
                        ingredient_quantity,
                        0,
                        ingredient_quantity,
                        ingredient_unit
                    ) ON CONFLICT (meal_plan_id, ingredient_name) DO UPDATE
                    SET 
                        total_quantity = ingredient_pools.total_quantity + EXCLUDED.total_quantity,
                        remaining_quantity = ingredient_pools.remaining_quantity + EXCLUDED.total_quantity;
                END LOOP;
            END IF;
        END LOOP;
    END IF;
END;
$$;

-- Grant execute permission
GRANT EXECUTE ON FUNCTION initialize_ingredient_pool(UUID, JSONB) TO authenticated;
GRANT EXECUTE ON FUNCTION initialize_ingredient_pool(UUID, JSONB) TO service_role;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'initialize_ingredient_pool function created successfully!';
END $$;