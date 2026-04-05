import React, { useState, useCallback, useEffect } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity,
  Dimensions, Modal, Pressable, ActivityIndicator, Image,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router, useFocusEffect } from 'expo-router';
import { Wifi, Bot, Bell, LogOut, ChevronRight, Plus } from 'lucide-react-native';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import { supabase } from '../lib/supabase';
import { Item } from '../data/mockData';
import { on } from '../lib/events';
import ItemCard from '../components/ItemCard';
import AddNewCard from '../components/AddNewCard';
import Logo from '../components/Logo';
import PnLChart, { PnLDataPoint } from '../components/PnLChart';


const { width: SCREEN_WIDTH } = Dimensions.get('window');
const CARD_WIDTH = Math.round(SCREEN_WIDTH * 0.58);

// ─── Helpers ──────────────────────────────────────────────────────────────────

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function mapDbItemToItem(row: any): Item {
  return {
    id: row.id,
    type: row.type,
    name: row.name,
    description: row.description ?? '',
    condition: row.condition ?? '',
    imageColor: row.image_color ?? '#93C5FD',
    targetPrice: row.target_price ?? 0,
    minPrice: row.min_price ?? undefined,
    maxPrice: row.max_price ?? undefined,
    autoAcceptThreshold: row.auto_accept_threshold ?? undefined,
    platforms: row.item_platforms?.map((p: any) => p.platform) ?? [],
    status: row.status ?? 'active',
    quantity: row.quantity ?? 1,
    negotiationStyle: row.negotiation_style ?? 'moderate',
    replyTone: row.reply_tone ?? 'professional',
    bestOffer: row.best_offer ?? undefined,
    initialPrice: row.initial_price ?? undefined,
    photos: row.item_photos
      ?.sort((a: any, b: any) => a.sort_order - b.sort_order)
      .map((p: any) => p.photo_url) ?? [],
    marketData: row.market_data?.map((md: any) => ({
      platform: md.platform,
      bestBuyPrice: md.best_buy_price,
      bestSellPrice: md.best_sell_price,
      volume: md.volume,
    })) ?? [],
    conversations: row.conversations?.map((c: any) => ({
      id: c.id,
      username: c.username,
      platform: c.platform,
      lastMessage: c.last_message ?? '',
      timestamp: c.last_message_at ? timeAgo(c.last_message_at) : '',
      unread: c.unread ?? false,
      messages: [],
    })) ?? [],
  };
}

export default function HomeScreen() {
  const { colors } = useTheme();
  const { user, signOut } = useAuth();
  const [profileMenuVisible, setProfileMenuVisible] = useState(false);
  const [items, setItems] = useState<Item[]>([]);
  const [pnlData, setPnlData] = useState<PnLDataPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);

  const displayName = user?.user_metadata?.display_name ?? user?.user_metadata?.full_name ?? user?.email ?? 'User';
  const initials = displayName
    .split(' ')
    .filter(Boolean)
    .map((w: string) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
  const email = user?.email ?? '';

  const refreshData = useCallback(async () => {
    if (!user) return;

    try {
      const [itemsResult, tradesResult] = await Promise.all([
        supabase
          .from('items')
          .select(`*, item_platforms(platform), item_photos(id, photo_url, sort_order), market_data(platform, best_buy_price, best_sell_price, volume), conversations(id, username, platform, last_message, last_message_at, unread)`)
          .eq('user_id', user.id)
          .neq('status', 'draft'),
        supabase
          .from('completed_trades')
          .select('*')
          .eq('user_id', user.id)
          .not('initial_price', 'is', null)
          .order('completed_at', { ascending: true }),
      ]);

      // Fetch profile avatar
      const { data: profileData } = await supabase
        .from('profiles')
        .select('avatar_url, display_name')
        .eq('id', user.id)
        .single();
      if (profileData?.avatar_url) setAvatarUrl(profileData.avatar_url);

      if (itemsResult.data) {
        // Sort raw data by last_viewed_at descending BEFORE mapping
        const sorted = [...itemsResult.data].sort((a: any, b: any) => {
          const aTime = new Date(a.last_viewed_at || 0).getTime();
          const bTime = new Date(b.last_viewed_at || 0).getTime();
          return bTime - aTime;
        });
        setItems(sorted.map(mapDbItemToItem));
      }

      if (tradesResult.data) {
        const chartData: PnLDataPoint[] = tradesResult.data.map((t: any) => {
          let profit = 0;
          if (t.type?.toLowerCase() === 'sold') {
            profit = (t.price ?? 0) - (t.initial_price ?? 0);
          } else {
            profit = (t.initial_price ?? 0) - (t.price ?? 0);
          }
          return {
            date: t.completed_at
              ? new Date(t.completed_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
              : '',
            isoDate: t.completed_at ?? '',
            value: profit,
          };
        });
        setPnlData(chartData);
      }
    } catch (err) {
      console.error('Failed to fetch data:', err);
    } finally {
      setLoading(false);
    }
  }, [user]);

  // Initial load
  useFocusEffect(
    useCallback(() => {
      refreshData();
    }, [refreshData])
  );

  // Listen for item status changes from detail page
  useEffect(() => {
    const offStatus = on('item:statusChanged', (itemId: string, newStatus: string) => {
      setItems(prev => prev.map(i => i.id === itemId ? { ...i, status: newStatus as any } : i));
    });
    const offDeleted = on('item:deleted', (itemId: string) => {
      setItems(prev => prev.filter(i => i.id !== itemId));
    });
    const offCreated = on('item:created', () => {
      refreshData();
    });
    return () => { offStatus(); offDeleted(); offCreated(); };
  }, [refreshData]);

  function handleItemPress(itemId: string) {
    // Optimistically move to front — applied immediately, visible when we return
    setItems(prev => {
      const idx = prev.findIndex(i => i.id === itemId);
      if (idx <= 0) return prev;
      const item = prev[idx];
      const rest = prev.filter((_, i) => i !== idx);
      const typeStart = rest.findIndex(i => i.type === item.type);
      if (typeStart === -1) return [item, ...rest];
      const result = [...rest];
      result.splice(typeStart, 0, item);
      return result;
    });
    router.push(`/item/${itemId}`);
  }

  const sellItems = items.filter(i => i.type === 'sell');
  const buyItems = items.filter(i => i.type === 'buy');

  if (loading) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: colors.surface, justifyContent: 'center', alignItems: 'center' }]} edges={['top']}>
        <ActivityIndicator size="large" color={colors.accent} />
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.surface }]} edges={['top']}>
      {/* Header */}
      <View style={[styles.header, { backgroundColor: colors.surface }]}>
        <Logo size={30} />
        <TouchableOpacity
          onPress={() => setProfileMenuVisible(true)}
          hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
          accessibilityLabel="Open profile menu"
        >
          {avatarUrl ? (
            <Image source={{ uri: avatarUrl }} style={styles.avatarBtn} />
          ) : (
            <View style={[styles.avatarBtn, { backgroundColor: colors.primary }]}>
              <Text style={styles.avatarInitials}>{initials}</Text>
            </View>
          )}
        </TouchableOpacity>
      </View>

      <View style={[styles.scrollWrap, { backgroundColor: colors.background }]}>
        <ScrollView
          style={styles.scroll}
          showsVerticalScrollIndicator={false}
          contentContainerStyle={styles.scrollContent}
        >
          {/* P&L Chart */}
          <View style={styles.chartSection}>
            <PnLChart data={pnlData} />
          </View>

          {/* Trades button */}
          <View style={styles.tradesButtonWrap}>
            <TouchableOpacity
              style={[styles.tradesButton, { backgroundColor: colors.surface }]}
              onPress={() => router.push('/trades')}
              activeOpacity={0.7}
            >
              <Text style={[styles.tradesButtonText, { color: colors.textPrimary }]}>Trades</Text>
              <ChevronRight size={14} color={colors.textMuted} />
            </TouchableOpacity>
          </View>

          {/* Selling */}
          <CarouselSection title="Selling" type="sell" items={sellItems} onItemPress={handleItemPress} />

          {/* Buying */}
          <CarouselSection title="Buying" type="buy" items={buyItems} onItemPress={handleItemPress} />
        </ScrollView>
      </View>

      {/* Profile Menu Modal */}
      <Modal
        visible={profileMenuVisible}
        transparent
        animationType="fade"
        onRequestClose={() => setProfileMenuVisible(false)}
      >
        <Pressable style={styles.modalOverlay} onPress={() => setProfileMenuVisible(false)}>
          <View style={[styles.profileMenu, { backgroundColor: colors.surface }]}>
            <TouchableOpacity
              style={[styles.profileMenuHeader, { borderBottomColor: colors.divider }]}
              onPress={() => { setProfileMenuVisible(false); router.push('/settings'); }}
              activeOpacity={0.7}
            >
              {avatarUrl ? (
                <Image source={{ uri: avatarUrl }} style={styles.profileMenuAvatar} />
              ) : (
                <View style={[styles.profileMenuAvatar, { backgroundColor: colors.primary }]}>
                  <Text style={styles.profileMenuAvatarText}>{initials}</Text>
                </View>
              )}
              <View style={{ flex: 1 }}>
                <Text style={[styles.profileMenuName, { color: colors.textPrimary }]}>{displayName}</Text>
                <Text style={[styles.profileMenuEmail, { color: colors.textMuted }]}>{email}</Text>
              </View>
              <ChevronRight size={14} color={colors.textMuted} />
            </TouchableOpacity>
            <ProfileMenuItem icon={<Wifi size={16} color={colors.textSecondary} />} label="Platforms" colors={colors} onPress={() => { setProfileMenuVisible(false); router.push('/settings/platforms'); }} />
            <View style={[styles.menuDivider, { backgroundColor: colors.divider }]} />
            <ProfileMenuItem icon={<Bot size={16} color={colors.textSecondary} />} label="Agent Behaviors" colors={colors} onPress={() => { setProfileMenuVisible(false); router.push('/settings/agents'); }} />
            <View style={[styles.menuDivider, { backgroundColor: colors.divider }]} />
            <ProfileMenuItem icon={<Bell size={16} color={colors.textSecondary} />} label="Notifications" colors={colors} onPress={() => { setProfileMenuVisible(false); router.push('/settings/notifications'); }} />
            <View style={[styles.menuDivider, { backgroundColor: colors.divider }]} />
            <ProfileMenuItem icon={<LogOut size={16} color={colors.destructive} />} label="Sign Out" colors={colors} textColor={colors.destructive} onPress={() => { setProfileMenuVisible(false); signOut(); }} />
          </View>
        </Pressable>
      </Modal>
    </SafeAreaView>
  );
}

// ─── Sub-components ────────────────────────────────────────────────────────────

function ProfileMenuItem({ icon, label, colors, textColor, onPress }: {
  icon: React.ReactNode; label: string; colors: any; textColor?: string; onPress: () => void;
}) {
  return (
    <TouchableOpacity style={styles.profileMenuItem} onPress={onPress}>
      {icon}
      <Text style={[styles.profileMenuItemText, { color: textColor ?? colors.textPrimary }]}>{label}</Text>
    </TouchableOpacity>
  );
}

function CarouselSection({ title, type, items, onItemPress }: { title: string; type: 'buy' | 'sell'; items: Item[]; onItemPress?: (id: string) => void }) {
  const { colors } = useTheme();
  const activeCount = items.filter(i => i.status === 'active').length;

  return (
    <View style={styles.section}>
      <View style={styles.sectionHeader}>
        <View style={styles.sectionLeft}>
          <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>{title}</Text>
          <AddNewCard onPress={() => router.push(`/new-listing?type=${type}`)} />
        </View>
        <Text style={[styles.countText, { color: colors.textMuted }]}>
          {activeCount}/{items.length} active
        </Text>
      </View>

      {items.length === 0 ? (
        <View style={emptyStyles.emptyCardWrap}>
          <TouchableOpacity
            style={[emptyStyles.emptyCard, { backgroundColor: colors.surface }]}
            onPress={() => router.push(`/new-listing?type=${type}`)}
            activeOpacity={0.7}
          >
            <Plus size={28} color={colors.textMuted} />
            <Text style={[emptyStyles.emptyCardTitle, { color: colors.textSecondary }]}>
              No items yet
            </Text>
            <Text style={[emptyStyles.emptyCardHint, { color: colors.textMuted }]}>
              Tap + to add your first {type === 'sell' ? 'sell' : 'buy'} agent
            </Text>
          </TouchableOpacity>
        </View>
      ) : (
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.carousel}
          decelerationRate="fast"
          snapToInterval={CARD_WIDTH + 12}
          snapToAlignment="start"
        >
          {items.map(item => (
            <ItemCard
              key={item.id}
              item={item}
              cardWidth={CARD_WIDTH}
              onPress={() => onItemPress ? onItemPress(item.id) : router.push(`/item/${item.id}`)}
            />
          ))}
        </ScrollView>
      )}
    </View>
  );
}

// ─── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1 },

  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingTop: 8,
    paddingBottom: 12,
  },
  avatarBtn: {
    width: 34,
    height: 34,
    borderRadius: 17,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarInitials: {
    fontSize: 12,
    fontWeight: '700',
    color: '#FFFFFF',
  },

  scrollWrap: { flex: 1 },
  scroll: { flex: 1 },
  scrollContent: { paddingBottom: 48 },

  chartSection: {
    marginHorizontal: 16,
    marginTop: 16,
  },

  tradesButtonWrap: {
    marginHorizontal: 16,
    marginTop: 16,
  },
  tradesButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 14,
  },
  tradesButtonText: {
    fontSize: 14,
    fontWeight: '600',
  },

  section: {
    marginTop: 28,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    marginBottom: 12,
  },
  sectionLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '700',
    letterSpacing: -0.3,
  },
  countText: {
    fontSize: 12,
    fontWeight: '500',
    fontVariant: ['tabular-nums'],
  },
  carousel: {
    paddingHorizontal: 16,
    gap: 12,
    paddingBottom: 4,
  },

  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-start',
    alignItems: 'flex-end',
    paddingTop: 80,
    paddingRight: 16,
  },
  profileMenu: {
    width: 220,
    borderRadius: 12,
    overflow: 'hidden',
  },
  profileMenuHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    padding: 14,
    borderBottomWidth: 1,
  },
  profileMenuAvatar: {
    width: 32,
    height: 32,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  profileMenuAvatarText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  profileMenuName: {
    fontSize: 14,
    fontWeight: '600',
  },
  profileMenuEmail: {
    fontSize: 12,
    marginTop: 1,
  },
  profileMenuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  profileMenuItemText: {
    fontSize: 14,
    fontWeight: '500',
  },
  menuDivider: {
    height: 1,
    marginHorizontal: 14,
  },
});

const emptyStyles = StyleSheet.create({
  emptyCardWrap: {
    paddingHorizontal: 16,
  },
  emptyCard: {
    borderRadius: 12,
    paddingVertical: 40,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    width: '100%',
  },
  emptyCardTitle: {
    fontSize: 15,
    fontWeight: '600',
    marginTop: 4,
  },
  emptyCardHint: {
    fontSize: 12,
    fontWeight: '500',
    textAlign: 'center',
    paddingHorizontal: 24,
  },
});
