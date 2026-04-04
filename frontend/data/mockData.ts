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
  price: number;
  volume: number;
  trend: number;
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
  autoRelist: boolean;
  marketData: MarketData[];
  conversations: Conversation[];
}

export const mockItems: Item[] = [
  {
    id: '1',
    type: 'sell',
    name: 'Air Jordan 1 Retro High OG',
    description: 'Chicago colorway, DS (deadstock). Box included. Size 10.',
    condition: 'New',
    imageColor: '#FCA5A5',
    targetPrice: 320,
    minPrice: 260,
    maxPrice: 380,
    autoAcceptThreshold: 300,
    platforms: ['depop', 'ebay', 'mercari'],
    status: 'active',
    quantity: 1,
    negotiationStyle: 'moderate',
    replyTone: 'professional',
    autoRelist: true,
    marketData: [
      { platform: 'depop', price: 315, volume: 42, trend: 3.2 },
      { platform: 'ebay', price: 332, volume: 128, trend: 1.8 },
      { platform: 'mercari', price: 298, volume: 67, trend: -0.5 },
    ],
    conversations: [
      {
        id: 'c1',
        username: 'sneaker_kylie',
        platform: 'depop',
        lastMessage: 'Would you take $280?',
        timestamp: '2m ago',
        unread: true,
        messages: [
          { id: 'm1', sender: 'them', text: 'Hey! Love these. Are they still available?', timestamp: '10:32 AM' },
          { id: 'm2', sender: 'agent', text: "Hi! Yes, still available. DS with original box. Happy to answer any questions!", timestamp: '10:33 AM' },
          { id: 'm3', sender: 'them', text: 'Would you take $280?', timestamp: '10:41 AM' },
          { id: 'm4', sender: 'agent', text: "Thanks for the offer! I'm firm at $310 given recent eBay sold comps averaging $330. Would you meet me at $310?", timestamp: '10:42 AM' },
        ],
      },
      {
        id: 'c2',
        username: 'j1collector',
        platform: 'ebay',
        lastMessage: 'Offer of $295 submitted',
        timestamp: '1h ago',
        unread: false,
        messages: [
          { id: 'm1', sender: 'them', text: 'Are these authentic?', timestamp: '9:15 AM' },
          { id: 'm2', sender: 'agent', text: 'Absolutely 100% authentic. I can provide purchase receipt and authentication photos.', timestamp: '9:16 AM' },
          { id: 'm3', sender: 'them', text: 'Offer of $295 submitted', timestamp: '9:45 AM' },
        ],
      },
    ],
  },
  {
    id: '2',
    type: 'sell',
    name: 'Sony WH-1000XM4',
    description: 'Excellent condition, barely used. Midnight blue. All accessories included.',
    condition: 'Like New',
    imageColor: '#93C5FD',
    targetPrice: 190,
    minPrice: 150,
    maxPrice: 220,
    autoAcceptThreshold: 175,
    platforms: ['depop', 'facebook', 'mercari'],
    status: 'active',
    quantity: 1,
    negotiationStyle: 'passive',
    replyTone: 'casual',
    autoRelist: false,
    marketData: [
      { platform: 'depop', price: 185, volume: 23, trend: -1.2 },
      { platform: 'facebook', price: 172, volume: 15, trend: -3.0 },
      { platform: 'mercari', price: 195, volume: 41, trend: 2.1 },
    ],
    conversations: [
      {
        id: 'c3',
        username: 'techwatcher',
        platform: 'mercari',
        lastMessage: 'Do they come with the case?',
        timestamp: '30m ago',
        unread: true,
        messages: [
          { id: 'm1', sender: 'them', text: 'Do they come with the case?', timestamp: '11:00 AM' },
          { id: 'm2', sender: 'agent', text: 'Yes! Comes with original Sony carry case, charging cable, aux cable, and all documentation.', timestamp: '11:01 AM' },
        ],
      },
    ],
  },
  {
    id: '3',
    type: 'sell',
    name: 'North Face Nuptse 700',
    description: "Vintage 90s Nuptse puffer. Navy blue. Size M. Minor fade on left arm.",
    condition: 'Good',
    imageColor: '#6EE7B7',
    targetPrice: 145,
    minPrice: 110,
    maxPrice: 180,
    platforms: ['depop', 'ebay'],
    status: 'paused',
    quantity: 1,
    negotiationStyle: 'moderate',
    replyTone: 'casual',
    autoRelist: false,
    marketData: [
      { platform: 'depop', price: 142, volume: 19, trend: 5.5 },
      { platform: 'ebay', price: 158, volume: 34, trend: 4.1 },
    ],
    conversations: [],
  },
  {
    id: '4',
    type: 'buy',
    name: 'Canon AE-1 Program',
    description: 'Looking for a clean body with working meter and shutter. Black preferred.',
    condition: 'Good',
    imageColor: '#FCD34D',
    targetPrice: 85,
    minPrice: 60,
    maxPrice: 120,
    autoAcceptThreshold: 90,
    platforms: ['ebay', 'depop', 'mercari', 'offerup'],
    status: 'active',
    quantity: 1,
    negotiationStyle: 'aggressive',
    replyTone: 'professional',
    autoRelist: false,
    marketData: [
      { platform: 'ebay', price: 98, volume: 87, trend: 2.3 },
      { platform: 'depop', price: 110, volume: 31, trend: 6.1 },
      { platform: 'mercari', price: 89, volume: 44, trend: -1.8 },
      { platform: 'offerup', price: 75, volume: 12, trend: -2.4 },
    ],
    conversations: [
      {
        id: 'c4',
        username: 'vintage_photo_co',
        platform: 'depop',
        lastMessage: "I can do $95 shipped.",
        timestamp: '15m ago',
        unread: true,
        messages: [
          { id: 'm1', sender: 'agent', text: "Hi! I've seen similar ones sell for around $80–90 recently. Would you consider $75 shipped? Happy to pay right away.", timestamp: '10:45 AM' },
          { id: 'm2', sender: 'them', text: "Hmm, I think it's worth more. Shutter sounds perfect on this one.", timestamp: '11:02 AM' },
          { id: 'm3', sender: 'agent', text: "Totally fair! Could you meet me at $85? I'm ready to buy today.", timestamp: '11:03 AM' },
          { id: 'm4', sender: 'them', text: "I can do $95 shipped.", timestamp: '11:18 AM' },
        ],
      },
      {
        id: 'c5',
        username: 'filmcameraseller',
        platform: 'ebay',
        lastMessage: 'Offer sent: $80',
        timestamp: '2h ago',
        unread: false,
        messages: [
          { id: 'm1', sender: 'agent', text: "Hi! I'd like to offer $80 shipped. Based on recent sales data, this is a fair market offer — I can pay immediately.", timestamp: '9:00 AM' },
          { id: 'm2', sender: 'them', text: 'Offer sent: $80', timestamp: '9:00 AM' },
        ],
      },
    ],
  },
  {
    id: '5',
    type: 'buy',
    name: 'Supreme Box Logo Hoodie FW20',
    description: 'Black or white preferred. Size L. Must be verified authentic.',
    condition: 'Good',
    imageColor: '#F9A8D4',
    targetPrice: 380,
    minPrice: 300,
    maxPrice: 450,
    autoAcceptThreshold: 400,
    platforms: ['depop', 'ebay', 'mercari'],
    status: 'active',
    quantity: 1,
    negotiationStyle: 'moderate',
    replyTone: 'professional',
    autoRelist: false,
    marketData: [
      { platform: 'depop', price: 410, volume: 8, trend: -2.1 },
      { platform: 'ebay', price: 425, volume: 22, trend: -0.8 },
      { platform: 'mercari', price: 395, volume: 11, trend: -3.2 },
    ],
    conversations: [
      {
        id: 'c6',
        username: 'supreme_resells',
        platform: 'depop',
        lastMessage: "Can't go lower than $400.",
        timestamp: '45m ago',
        unread: false,
        messages: [
          { id: 'm1', sender: 'agent', text: "Hey! Recent eBay sold prices average around $380 for FW20 box logo. Would you consider $360?", timestamp: '10:00 AM' },
          { id: 'm2', sender: 'them', text: "Can't go lower than $400.", timestamp: '10:15 AM' },
        ],
      },
    ],
  },
];
