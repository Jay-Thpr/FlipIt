-- Stagger last_viewed_at for existing items so sorting works immediately
-- Run in Supabase SQL Editor
UPDATE public.items SET last_viewed_at = created_at;
