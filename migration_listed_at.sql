-- Run this in Supabase SQL Editor to add listed_at column
ALTER TABLE public.completed_trades ADD COLUMN IF NOT EXISTS listed_at TIMESTAMPTZ;
