import React, { useState } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity,
  Dimensions, Modal, Pressable,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Settings, LogOut } from 'lucide-react-native';
import { useTheme } from '../contexts/ThemeContext';
import { mockItems, Item } from '../data/mockData';
import ItemCard from '../components/ItemCard';
import AddNewCard from '../components/AddNewCard';

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const CARD_WIDTH = Math.round(SCREEN_WIDTH * 0.58);
const AGENT_LIMIT = 10;

export default function HomeScreen() {
  const { colors } = useTheme();
  const [profileMenuVisible, setProfileMenuVisible] = useState(false);
  const sellItems = mockItems.filter(i => i.type === 'sell');
  const buyItems = mockItems.filter(i => i.type === 'buy');

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.surface }]} edges={['top']}>
      {/* Header */}
      <View style={[styles.header, { backgroundColor: colors.surface }]}>
        <View style={styles.headerLeft}>
          <Text style={[styles.appName, { color: colors.textPrimary }]}>AgentMarket</Text>
          <View style={[styles.agentCounter, { backgroundColor: colors.surface }]}>
            <Text style={[styles.agentCounterText, { color: colors.textMuted }]}>
              {mockItems.length}/{AGENT_LIMIT}
            </Text>
          </View>
        </View>
        <TouchableOpacity
          style={[styles.avatarBtn, { backgroundColor: colors.primary }]}
          onPress={() => setProfileMenuVisible(true)}
          hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
          accessibilityLabel="Open profile menu"
        >
          <Text style={styles.avatarInitials}>SS</Text>
        </TouchableOpacity>
      </View>

      <View style={[styles.scrollWrap, { backgroundColor: colors.background }]}>
        <ScrollView
          style={styles.scroll}
          showsVerticalScrollIndicator={false}
          contentContainerStyle={styles.scrollContent}
        >
          <CarouselSection title="Selling" type="sell" items={sellItems} />
          <CarouselSection title="Buying" type="buy" items={buyItems} />
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
            <View style={[styles.profileMenuHeader, { borderBottomColor: colors.divider }]}>
              <View style={[styles.profileMenuAvatar, { backgroundColor: colors.primary }]}>
                <Text style={styles.profileMenuAvatarText}>SS</Text>
              </View>
              <View>
                <Text style={[styles.profileMenuName, { color: colors.textPrimary }]}>Sam S.</Text>
                <Text style={[styles.profileMenuEmail, { color: colors.textMuted }]}>sam@example.com</Text>
              </View>
            </View>
            <TouchableOpacity
              style={styles.profileMenuItem}
              onPress={() => {
                setProfileMenuVisible(false);
                router.push('/settings');
              }}
            >
              <Settings size={16} color={colors.textSecondary} />
              <Text style={[styles.profileMenuItemText, { color: colors.textPrimary }]}>Settings</Text>
            </TouchableOpacity>
            <View style={[styles.menuDivider, { backgroundColor: colors.divider }]} />
            <TouchableOpacity
              style={styles.profileMenuItem}
              onPress={() => setProfileMenuVisible(false)}
            >
              <LogOut size={16} color={colors.destructive} />
              <Text style={[styles.profileMenuItemText, { color: colors.destructive }]}>Sign Out</Text>
            </TouchableOpacity>
          </View>
        </Pressable>
      </Modal>
    </SafeAreaView>
  );
}

function CarouselSection({ title, type, items }: { title: string; type: 'buy' | 'sell'; items: Item[] }) {
  const { colors } = useTheme();
  const activeCount = items.filter(i => i.status === 'active').length;

  return (
    <View style={styles.section}>
      {/* Section header: title + add button on left, count on right */}
      <View style={styles.sectionHeader}>
        <View style={styles.sectionLeft}>
          <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>{title}</Text>
          <AddNewCard onPress={() => router.push(`/new-listing?type=${type}`)} />
        </View>
        <Text style={[styles.countText, { color: colors.textMuted }]}>
          {activeCount}/{items.length} active
        </Text>
      </View>

      {/* Carousel */}
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
            onPress={() => router.push(`/item/${item.id}`)}
          />
        ))}
      </ScrollView>
    </View>
  );
}

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
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  appName: {
    fontSize: 20,
    fontWeight: '800',
    letterSpacing: -0.5,
  },
  agentCounter: {
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  agentCounterText: {
    fontSize: 12,
    fontWeight: '600',
    fontVariant: ['tabular-nums'],
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

  section: {
    paddingTop: 24,
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

  // Profile menu modal
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
