-- Migration: Add response_delay to items, make target_price nullable
-- Run this in Supabase Dashboard > SQL Editor

-- 1. Add response_delay column to items
ALTER TABLE public.items
ADD COLUMN IF NOT EXISTS response_delay TEXT NOT NULL DEFAULT '5 min'
CHECK (response_delay IN ('1 min', '5 min', '15 min', '30 min'));

-- 2. Make target_price nullable (no longer a required field)
ALTER TABLE public.items ALTER COLUMN target_price DROP NOT NULL;
