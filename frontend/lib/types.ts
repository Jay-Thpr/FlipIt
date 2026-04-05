// Database types matching BACKEND_REQUIREMENTS.md schema
// These are used by the Supabase client for type safety.

export type Platform = 'ebay' | 'depop' | 'mercari' | 'offerup' | 'facebook';
export type ItemStatus = 'active' | 'paused' | 'archived' | 'draft';
export type ItemType = 'buy' | 'sell';
export type NegotiationStyle = 'aggressive' | 'moderate' | 'passive';
export type ReplyTone = 'professional' | 'casual' | 'firm';

export interface Profile {
  id: string;
  display_name: string;
  email: string;
  avatar_url: string | null;
  created_at: string;
}

export interface UserSettings {
  user_id: string;
  theme_preference: 'light' | 'dark' | 'system';
  auto_reply: boolean;
  response_delay: string;
  negotiation_style: NegotiationStyle;
  reply_tone: ReplyTone;
  notif_new_message: boolean;
  notif_price_drop: boolean;
  notif_deal_closed: boolean;
  notif_listing_expired: boolean;
  updated_at: string;
}

export interface PlatformConnection {
  id: string;
  user_id: string;
  platform: Platform;
  username: string | null;
  connected: boolean;
  connected_at: string | null;
}

export interface DbItem {
  id: string;
  user_id: string;
  type: ItemType;
  name: string;
  description: string;
  condition: string;
  image_color: string;
  target_price: number;
  min_price: number | null;
  max_price: number | null;
  auto_accept_threshold: number | null;
  initial_price: number | null;
  status: ItemStatus;
  quantity: number;
  negotiation_style: NegotiationStyle;
  reply_tone: ReplyTone;
  best_offer: number | null;
  draft_url: string | null;
  listing_screenshot_url: string | null;
  listing_preview_payload: any | null;
  created_at: string;
  updated_at: string;
  last_viewed_at: string;
  // Joined relations
  item_platforms?: { platform: Platform }[];
  item_photos?: DbItemPhoto[];
  market_data?: DbMarketData[];
  conversations?: DbConversation[];
}

export interface DbItemPhoto {
  id: string;
  item_id: string;
  photo_url: string;
  sort_order: number;
  created_at: string;
}

export interface DbMarketData {
  id: string;
  item_id: string;
  platform: Platform;
  best_buy_price: number;
  best_sell_price: number;
  volume: number;
  updated_at: string;
}

export interface DbConversation {
  id: string;
  item_id: string | null;
  user_id: string | null;
  username: string;
  platform: Platform;
  last_message: string;
  last_message_at: string;
  unread: boolean;
  listing_url: string | null;
  listing_title: string | null;
  seller: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  messages?: DbMessage[];
}

export interface DbMessage {
  id: string;
  conversation_id: string;
  sender: 'agent' | 'them';
  text: string;
  created_at: string;
}

export interface DbCompletedTrade {
  id: string;
  user_id: string;
  item_id: string | null;
  name: string;
  type: 'Sold' | 'Bought';
  platform: string;
  price: number;
  initial_price: number | null;
  listed_at: string | null;
  completed_at: string;
}

// We skip the full Database generic type to avoid complex type gymnastics.
// The Supabase client is untyped; use the interfaces above for manual casting.
// e.g.: const { data } = await supabase.from('items').select('*') as { data: DbItem[] | null }
export type Database = any;
