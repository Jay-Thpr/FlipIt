-- Run in Supabase SQL Editor
ALTER TABLE public.items ADD COLUMN IF NOT EXISTS last_viewed_at TIMESTAMPTZ NOT NULL DEFAULT now();
