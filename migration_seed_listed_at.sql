-- Updates existing seed trades with realistic listed_at dates
-- (each item was listed 2-5 days before it sold)
-- Run in Supabase SQL Editor

UPDATE public.completed_trades SET listed_at = completed_at - interval '3 days' WHERE name = 'Nike Dunk Low Panda';
UPDATE public.completed_trades SET listed_at = completed_at - interval '5 days' WHERE name = 'Vintage Levi 501s';
UPDATE public.completed_trades SET listed_at = completed_at - interval '2 days' WHERE name = 'Canon AE-1 Body';
UPDATE public.completed_trades SET listed_at = completed_at - interval '4 days' WHERE name = 'Ray-Ban Aviators';
UPDATE public.completed_trades SET listed_at = completed_at - interval '2 days' WHERE name = 'Bose QC45';
UPDATE public.completed_trades SET listed_at = completed_at - interval '3 days' WHERE name = 'Supreme Beanie';
UPDATE public.completed_trades SET listed_at = completed_at - interval '1 day' WHERE name = 'PS5 DualSense';
UPDATE public.completed_trades SET listed_at = completed_at - interval '6 days' WHERE name = 'Patagonia Fleece';
UPDATE public.completed_trades SET listed_at = completed_at - interval '2 days' WHERE name = 'AirPods Pro 2';
UPDATE public.completed_trades SET listed_at = completed_at - interval '4 days' WHERE name = 'Vintage Polaroid';
UPDATE public.completed_trades SET listed_at = completed_at - interval '7 days' WHERE name = 'North Face Puffer';
UPDATE public.completed_trades SET listed_at = completed_at - interval '3 days' WHERE name = 'Mechanical Keyboard';
