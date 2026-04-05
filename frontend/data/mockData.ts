export type Platform = 'ebay' | 'depop' | 'mercari' | 'offerup' | 'facebook';
export type ItemStatus = 'active' | 'paused' | 'archived';
export type ItemType = 'buy' | 'sell';
export type NegotiationStyle = 'aggressive' | 'moderate' | 'passive';
export type ReplyTone = 'professional' | 'casual' | 'firm';

export interface Message {
  id: string;
  sender: 'agent' | 'them';
  text: string;
  timestamp: string;
}

export interface Conversation {
  id: string;
  username: string;
  platform: Platform;
  lastMessage: string;
  timestamp: string;
  unread: boolean;
  messages: Message[];
}

export interface MarketData {
  platform: Platform;
  bestBuyPrice: number;
  bestSellPrice: number;
  volume: number;
}

export interface Item {
  id: string;
  type: ItemType;
  name: string;
  description: string;
  condition: string;
  imageColor: string;
  targetPrice: number;
  minPrice?: number;
  maxPrice?: number;
  autoAcceptThreshold?: number;
  platforms: Platform[];
  status: ItemStatus;
  quantity: number;
  negotiationStyle: NegotiationStyle;
  replyTone: ReplyTone;
  bestOffer?: number;
  initialPrice?: number;
  photos: string[];
  marketData: MarketData[];
  conversations: Conversation[];
}

export const PLATFORM_NAMES: Record<Platform, string> = {
  ebay: 'eBay',
  depop: 'Depop',
  mercari: 'Mercari',
  offerup: 'OfferUp',
  facebook: 'Facebook',
};

import AsyncStorage from '@react-native-async-storage/async-storage';

export const mockItems: Item[] = [
  // ... (keeping existing 3 items)
  {
    id: '6',
    type: 'sell',
    name: 'Project Social T "Champagne" Graphic Tee',
    description: 'Vintage-style Champagne graphic on a high-quality 100% cotton black crewneck. One size, relaxed fit.',
    condition: 'Very Good',
    imageColor: '#1A1A1A',
    targetPrice: 10.99,
    minPrice: 6.00,
    maxPrice: 15.00,
    autoAcceptThreshold: 10.00,
    platforms: ['ebay', 'depop', 'mercari'],
    status: 'active',
    quantity: 1,
    negotiationStyle: 'moderate',
    replyTone: 'professional',
    initialPrice: 32.00,
    bestOffer: 8.50,
    photos: ['assets/champagne-tee.png'],
    marketData: [
      { platform: 'ebay', bestBuyPrice: 9.99, bestSellPrice: 12.50, volume: 18 },
      { platform: 'depop', bestBuyPrice: 14.00, bestSellPrice: 16.00, volume: 7 },
      { platform: 'mercari', bestBuyPrice: 10.50, bestSellPrice: 12.00, volume: 11 },
    ],
    conversations: [
      {
        id: 'c-social-1',
        username: 'graphichunter_22',
        platform: 'depop',
        lastMessage: 'Would you take $8.50? Can pay now.',
        timestamp: '5m ago',
        unread: true,
        messages: [
          { id: 'm1', sender: 'them', text: 'Hey! Is this still available?', timestamp: '2:15 PM' },
          { id: 'm2', sender: 'agent', text: 'Hi there! Yes, the Champagne graphic tee is still available and in great condition.', timestamp: '2:16 PM' },
          { id: 'm3', sender: 'them', text: 'Would you take $8.50? Can pay now.', timestamp: '2:21 PM' },
        ],
      },
      {
        id: 'c-social-2',
        username: 'streetwear_sam',
        platform: 'ebay',
        lastMessage: 'How fast do you ship?',
        timestamp: '1h ago',
        unread: false,
        messages: [
          { id: 'm1', sender: 'them', text: 'Love the design. How fast do you typically ship out?', timestamp: '1:00 PM' },
          { id: 'm2', sender: 'agent', text: 'Thanks! I usually ship within 24 hours of payment. If you order today, it will go out tomorrow morning via USPS Ground Advantage.', timestamp: '1:05 PM' },
          { id: 'm3', sender: 'them', text: 'Awesome, thanks!', timestamp: '1:10 PM' },
        ],
      },
    ],
  },
  {
    id: '3',
    type: 'sell',
    name: 'North Face Nuptse 700',
    description: 'Vintage 90s Nuptse puffer. Navy blue. Size M. Minor fade on left arm.',
    condition: 'Good',
    imageColor: '#6EE7B7',
    targetPrice: 145.00,
    minPrice: 110.00,
    maxPrice: 180.00,
    platforms: ['depop', 'ebay'],
    status: 'paused',
    quantity: 1,
    negotiationStyle: 'moderate',
    replyTone: 'casual',
    photos: ['assets/north-face.png'],
    marketData: [
      { platform: 'depop', bestBuyPrice: 130, bestSellPrice: 142, volume: 19 },
      { platform: 'ebay', bestBuyPrice: 145, bestSellPrice: 158, volume: 34 },
    ],
    conversations: [
      {
        id: 'c-nuptse-1',
        username: 'winter_is_coming',
        platform: 'ebay',
        lastMessage: 'Could you meet me at $135?',
        timestamp: '20m ago',
        unread: true,
        messages: [
          { id: 'm1', sender: 'them', text: 'Hey, would you take $120 for this?', timestamp: '10:45 AM' },
          { id: 'm2', sender: 'agent', text: 'Hi! Thanks for the offer. Since this is a vintage 90s piece in such great condition, I’m looking for at least $140. Could you do $140?', timestamp: '10:50 AM' },
          { id: 'm3', sender: 'them', text: 'It has that fade on the arm though... Could you meet me at $135?', timestamp: '11:02 AM' },
        ],
      },
      {
        id: 'c-nuptse-2',
        username: 'puffer_enthusiast',
        platform: 'depop',
        lastMessage: 'Can I see a photo of the fade?',
        timestamp: '2h ago',
        unread: false,
        messages: [
          { id: 'm1', sender: 'them', text: 'Hey! Is the fade very noticeable in person?', timestamp: '9:00 AM' },
          { id: 'm2', sender: 'agent', text: 'It’s quite subtle, just typical vintage wear. I’ve added a close-up photo to the gallery so you can see it clearly!', timestamp: '9:15 AM' },
          { id: 'm3', sender: 'them', text: 'Cool, let me check it out.', timestamp: '9:20 AM' },
        ],
      },
    ],
  },
  {
    id: '7',
    type: 'buy',
    name: 'Sublime "Sun" Rock Band Graphic Retro Tee',
    description: 'Looking for the vintage-style Sublime sun logo graphic tee. Washed black/grey finish preferred. Oversized fit.',
    condition: 'Very Good',
    imageColor: '#2D2D2D',
    targetPrice: 1.50,
    minPrice: 1.00,
    maxPrice: 3.00,
    platforms: ['ebay', 'depop', 'mercari'],
    status: 'active',
    quantity: 1,
    negotiationStyle: 'aggressive',
    replyTone: 'casual',
    photos: ['assets/sublime.png'],
    marketData: [
      { platform: 'ebay', bestBuyPrice: 1.38, bestSellPrice: 2.38, volume: 45 },
      { platform: 'depop', bestBuyPrice: 5.00, bestSellPrice: 8.00, volume: 12 },
    ],
    conversations: [
      {
        id: 'c-sublime-1',
        username: 'vintage_vibes_90s',
        platform: 'ebay',
        lastMessage: 'I can do $1.38 + shipping. Let me know!',
        timestamp: '10m ago',
        unread: true,
        messages: [
          { id: 'm1', sender: 'agent', text: 'Hey! I saw your listing for the Sublime tee. I’m looking for this specific washed black version. Is the price flexible?', timestamp: '3:00 PM' },
          { id: 'm2', sender: 'them', text: 'Hey! Yeah, I can be a bit flexible. It’s exactly that retro washed look.', timestamp: '3:05 PM' },
          { id: 'm3', sender: 'agent', text: 'Great! Would you consider $1.38? Ready to buy now.', timestamp: '3:06 PM' },
          { id: 'm4', sender: 'them', text: 'I can do $1.38 + shipping. Let me know!', timestamp: '3:10 PM' },
        ],
      },
      {
        id: 'c-sublime-2',
        username: 'music_thread_store',
        platform: 'mercari',
        lastMessage: 'Sorry, just sold!',
        timestamp: '1d ago',
        unread: false,
        messages: [
          { id: 'm1', sender: 'agent', text: 'Hi! Is this still available for $2.00?', timestamp: 'Yesterday' },
          { id: 'm2', sender: 'them', text: 'Sorry, just sold!', timestamp: 'Yesterday' },
        ],
      },
    ],
  },
];

// Local state for items created during the session
let localCreatedItems: Item[] = [];

const LOCAL_STORAGE_KEY = 'diamondhacks_local_items';

export async function loadLocalItems() {
  try {
    const stored = await AsyncStorage.getItem(LOCAL_STORAGE_KEY);
    if (stored) {
      localCreatedItems = JSON.parse(stored);
    }
  } catch (e) {
    console.error('Failed to load local items:', e);
  }
}

export async function addLocalItem(item: Item) {
  localCreatedItems.push(item);
  try {
    await AsyncStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(localCreatedItems));
  } catch (e) {
    console.error('Failed to save local items:', e);
  }
}

export function getLocalItems(): Item[] {
  return localCreatedItems;
}

export interface Trade {
  id: string;
  itemName: string;
  buyPrice: number;
  sellPrice: number;
  date: string; // ISO date
  platform: Platform;
}

export const mockTrades: Trade[] = [
  { id: 't1', itemName: 'Stussy World Tour Tee', buyPrice: 12.00, sellPrice: 28.00, date: '2026-03-01T10:00:00Z', platform: 'depop' }, // +16
  { id: 't2', itemName: 'Vintage Carhartt Beanie', buyPrice: 5.00, sellPrice: 18.00, date: '2026-03-03T14:30:00Z', platform: 'ebay' }, // +13 (29)
  { id: 't3', itemName: 'Essentials Tee Cream', buyPrice: 20.00, sellPrice: 42.00, date: '2026-03-05T09:15:00Z', platform: 'mercari' }, // +22 (51)
  { id: 't4', itemName: 'Patagonia Duckbill Cap', buyPrice: 15.00, sellPrice: 32.00, date: '2026-03-08T16:45:00Z', platform: 'ebay' }, // +17 (68)
  { id: 't5', itemName: 'Vintage Nike Windbreaker', buyPrice: 10.00, sellPrice: 35.00, date: '2026-03-10T11:20:00Z', platform: 'depop' }, // +25 (93)
  { id: 't6', itemName: 'Adidas Gazelle Indoor', buyPrice: 45.00, sellPrice: 75.00, date: '2026-03-12T15:00:00Z', platform: 'ebay' }, // +30 (123)
  { id: 't7', itemName: 'Champion Reverse Weave', buyPrice: 8.00, sellPrice: 28.00, date: '2026-03-15T12:30:00Z', platform: 'mercari' }, // +20 (143)
  { id: 't8', itemName: 'Vintage Levi\'s 501', buyPrice: 15.00, sellPrice: 40.00, date: '2026-03-18T10:00:00Z', platform: 'ebay' }, // +25 (168)
  { id: 't9', itemName: 'North Face Denali Fleece', buyPrice: 35.00, sellPrice: 65.00, date: '2026-03-22T14:00:00Z', platform: 'depop' }, // +30 (198)
  { id: 't10', itemName: 'Carhartt WIP Pocket Tee', buyPrice: 15.00, sellPrice: 28.00, date: '2026-03-25T16:20:00Z', platform: 'ebay' }, // +13 (211)
  { id: 't11', itemName: 'Uniqlo U Lemaire Shirt', buyPrice: 10.00, sellPrice: 22.00, date: '2026-03-28T11:45:00Z', platform: 'mercari' }, // +12 (223)
  { id: 't12', itemName: 'Vintage Harley Davidson Tee', buyPrice: 8.00, sellPrice: 20.00, date: '2026-03-31T09:30:00Z', platform: 'ebay' }, // +12 (235)
  { id: 't13', itemName: 'Dickies 874 Work Pants', buyPrice: 12.00, sellPrice: 25.00, date: '2026-04-01T15:10:00Z', platform: 'depop' }, // +13 (248)
  { id: 't14', itemName: 'Vintage Blank Hoodie', buyPrice: 5.00, sellPrice: 15.00, date: '2026-04-03T18:00:00Z', platform: 'ebay' }, // +10 (258)
  { id: 't15', itemName: 'Old Navy Parachute Pants', buyPrice: 10.00, sellPrice: 22.00, date: '2026-04-04T12:00:00Z', platform: 'mercari' }, // +12 (270)
];

export function getPnLData() {
  const sorted = [...mockTrades].sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
  let runningTotal = 0;
  
  // Create a proper cumulative curve
  const dataPoints = sorted.map(t => {
    const profit = t.sellPrice - t.buyPrice;
    runningTotal += profit;
    const date = new Date(t.date);
    return {
      date: date.toLocaleDateString([], { month: 'short', day: 'numeric' }),
      isoDate: t.date,
      value: Math.round(runningTotal), // Keep values clean
    };
  });

  // Always start the graph at $0 if no trades, but for demo we start with 0 as first point
  return [{ date: 'Start', value: 0 }, ...dataPoints];
}

export function getAllItems(): Item[] {
  return [...mockItems, ...localCreatedItems];
}
