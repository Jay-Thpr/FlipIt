-- ============================================================
-- FlipIt Demo Data — Paste in Supabase SQL Editor
-- REPLACE 'YOUR_USER_ID' with your UUID from Authentication > Users
-- ============================================================

DO $$
DECLARE
  uid UUID := 'da303e1a-be19-434e-b98d-99ee5f02bbda';  -- <-- REPLACE THIS
  item1 UUID := gen_random_uuid();
  item2 UUID := gen_random_uuid();
  item3 UUID := gen_random_uuid();
  item4 UUID := gen_random_uuid();
  item5 UUID := gen_random_uuid();
  conv1 UUID := gen_random_uuid();
  conv2 UUID := gen_random_uuid();
  conv3 UUID := gen_random_uuid();
  conv4 UUID := gen_random_uuid();
BEGIN

-- ============================================================
-- Items
-- ============================================================
INSERT INTO public.items (id, user_id, type, name, description, condition, image_color, target_price, min_price, max_price, auto_accept_threshold, initial_price, status, quantity, negotiation_style, reply_tone, best_offer) VALUES
  (item1, uid, 'sell', 'Air Jordan 1 Retro High OG', 'Chicago colorway, DS (deadstock). Box included. Size 10.', 'New', '#FCA5A5', 320, 260, 380, 300, 85, 'active', 1, 'moderate', 'professional', 295),
  (item2, uid, 'sell', 'Sony WH-1000XM4', 'Excellent condition, barely used. Midnight blue. All accessories included.', 'Like New', '#93C5FD', 190, 150, 220, 175, 45, 'active', 1, 'passive', 'casual', NULL),
  (item3, uid, 'sell', 'North Face Nuptse 700', 'Vintage 90s Nuptse puffer. Navy blue. Size M. Minor fade on left arm.', 'Good', '#6EE7B7', 145, 110, 180, NULL, NULL, 'paused', 1, 'moderate', 'casual', NULL),
  (item4, uid, 'buy', 'Canon AE-1 Program', 'Looking for a clean body with working meter and shutter. Black preferred.', 'Good', '#FCD34D', 85, 60, 120, 90, NULL, 'active', 1, 'aggressive', 'professional', 95),
  (item5, uid, 'buy', 'Supreme Box Logo Hoodie FW20', 'Black or white preferred. Size L. Must be verified authentic.', 'Good', '#F9A8D4', 380, 300, 450, 400, NULL, 'active', 1, 'moderate', 'professional', NULL);

-- ============================================================
-- Item Platforms
-- ============================================================
INSERT INTO public.item_platforms (item_id, platform) VALUES
  (item1, 'depop'), (item1, 'ebay'), (item1, 'mercari'),
  (item2, 'depop'), (item2, 'facebook'), (item2, 'mercari'),
  (item3, 'depop'), (item3, 'ebay'),
  (item4, 'ebay'), (item4, 'depop'), (item4, 'mercari'), (item4, 'offerup'),
  (item5, 'depop'), (item5, 'ebay'), (item5, 'mercari');

-- ============================================================
-- Market Data
-- ============================================================
INSERT INTO public.market_data (item_id, platform, best_buy_price, best_sell_price, volume) VALUES
  (item1, 'depop', 299, 315, 42),
  (item1, 'ebay', 310, 332, 128),
  (item1, 'mercari', 285, 298, 67),
  (item2, 'depop', 170, 185, 23),
  (item2, 'facebook', 160, 172, 15),
  (item2, 'mercari', 180, 195, 41),
  (item3, 'depop', 130, 142, 19),
  (item3, 'ebay', 145, 158, 34),
  (item4, 'ebay', 85, 98, 87),
  (item4, 'depop', 95, 110, 31),
  (item4, 'mercari', 80, 89, 44),
  (item4, 'offerup', 65, 75, 12),
  (item5, 'depop', 390, 410, 8),
  (item5, 'ebay', 405, 425, 22),
  (item5, 'mercari', 375, 395, 11);

-- ============================================================
-- Conversations
-- ============================================================
INSERT INTO public.conversations (id, item_id, username, platform, last_message, last_message_at, unread) VALUES
  (conv1, item1, 'sneaker_kylie', 'depop', 'Would you take $280?', now() - interval '2 minutes', true),
  (conv2, item1, 'j1collector', 'ebay', 'Offer of $295 submitted', now() - interval '1 hour', false),
  (conv3, item4, 'vintage_photo_co', 'depop', 'I can do $95 shipped.', now() - interval '15 minutes', true),
  (conv4, item5, 'supreme_resells', 'depop', 'Can''t go lower than $400.', now() - interval '45 minutes', false);

-- ============================================================
-- Messages
-- ============================================================
INSERT INTO public.messages (conversation_id, sender, text, created_at) VALUES
  (conv1, 'them',  'Hey! Love these. Are they still available?', now() - interval '15 minutes'),
  (conv1, 'agent', 'Hi! Yes, still available. DS with original box. Happy to answer any questions!', now() - interval '14 minutes'),
  (conv1, 'them',  'Would you take $280?', now() - interval '6 minutes'),
  (conv1, 'agent', 'Thanks for the offer! I''m firm at $310 given recent eBay sold comps averaging $330. Would you meet me at $310?', now() - interval '5 minutes'),

  (conv2, 'them',  'Are these authentic?', now() - interval '2 hours'),
  (conv2, 'agent', 'Absolutely 100% authentic. I can provide purchase receipt and authentication photos.', now() - interval '119 minutes'),
  (conv2, 'them',  'Offer of $295 submitted', now() - interval '90 minutes'),

  (conv3, 'agent', 'Hi! I''ve seen similar ones sell for around $80-90 recently. Would you consider $75 shipped?', now() - interval '50 minutes'),
  (conv3, 'them',  'Hmm, I think it''s worth more. Shutter sounds perfect on this one.', now() - interval '33 minutes'),
  (conv3, 'agent', 'Totally fair! Could you meet me at $85? I''m ready to buy today.', now() - interval '32 minutes'),
  (conv3, 'them',  'I can do $95 shipped.', now() - interval '17 minutes'),

  (conv4, 'agent', 'Hey! Recent eBay sold prices average around $380 for FW20 box logo. Would you consider $360?', now() - interval '1 hour'),
  (conv4, 'them',  'Can''t go lower than $400.', now() - interval '45 minutes');

-- ============================================================
-- Completed Trades (this feeds the P&L chart)
-- ============================================================
INSERT INTO public.completed_trades (user_id, name, type, platform, price, initial_price, completed_at) VALUES
  (uid, 'Nike Dunk Low Panda',   'Sold',   'ebay',     145, 93,   now() - interval '7 days'),
  (uid, 'Vintage Levi 501s',     'Sold',   'depop',    68,  12,   now() - interval '10 days'),
  (uid, 'Canon AE-1 Body',       'Bought', 'mercari',  82,  NULL, now() - interval '13 days'),
  (uid, 'Ray-Ban Aviators',      'Sold',   'facebook', 85,  95,   now() - interval '17 days'),
  (uid, 'Bose QC45',             'Sold',   'ebay',     195, 120,  now() - interval '20 days'),
  (uid, 'Supreme Beanie',        'Bought', 'depop',    45,  NULL, now() - interval '23 days'),
  (uid, 'PS5 DualSense',         'Sold',   'mercari',  42,  28,   now() - interval '25 days'),
  (uid, 'Patagonia Fleece',      'Sold',   'ebay',     78,  15,   now() - interval '27 days'),
  (uid, 'AirPods Pro 2',         'Sold',   'facebook', 165, 130,  now() - interval '30 days'),
  (uid, 'Vintage Polaroid',      'Bought', 'ebay',     55,  120,  now() - interval '33 days'),
  (uid, 'North Face Puffer',     'Sold',   'depop',    125, 35,   now() - interval '37 days'),
  (uid, 'Mechanical Keyboard',   'Sold',   'mercari',  95,  NULL, now() - interval '40 days');

END $$;
