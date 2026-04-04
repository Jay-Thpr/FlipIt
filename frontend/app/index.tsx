import React, { useState } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity,
  Dimensions, Modal, Pressable,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { Settings, User, LogOut } from 'lucide-react-native';
import { useTheme } from '../contexts/ThemeContext';
import { mockItems, Item } from '../data/mockData';
import ItemCard from '../components/ItemCard';
import AddNewCard from '../components/AddNewCard';

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const CARD_WIDTH = Math.round(SCREEN_WIDTH * 0.44);
const AGENT_LIMIT = 10;

export default function HomeScreen() {
  const { colors } = useTheme();
  const [profileMenuVisible, setProfileMenuVisible] = useState(false);
  const sellItems = mockItems.filter(i => i.type === 'sell');
  const buyItems = mockItems.filter(i => i.type === 'buy');
  const activeCount = mockItems.filter(i => i.status === 'active').length;

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]}>
      {/* Header */}
      <View style={[styles.header, { borderBottomColor: colors.border }]}>
        <View style={styles.headerLeft}>
          <Text style={[styles.appName, { color: colors.primary }]}>AgentMarket</Text>
          <View style={[styles.agentCounter, { backgroundColor: colors.surface, borderColor: colors.border }]}>
            <Text style={[styles.agentCounterText, { color: colors.textSecondary }]}>
              {activeCount} / {AGENT_LIMIT} Agents in Use
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

      <ScrollView
        style={styles.scroll}
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
      >
        <CarouselSection title="Selling" items={sellItems} />
        <CarouselSection title="Buying" items={buyItems} />
      </ScrollView>

      {/* Profile Menu Modal */}
      <Modal
        visible={profileMenuVisible}
        transparent
        animationType="fade"
        onRequestClose={() => setProfileMenuVisible(false)}
      >
        <Pressable style={styles.modalOverlay} onPress={() => setProfileMenuVisible(false)}>
          <View style={[styles.profileMenu, { backgroundColor: colors.surface, borderColor: colors.border }]}>
            <View style={[styles.profileMenuHeader, { borderBottomColor: colors.border }]}>
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
            <View style={[styles.menuDivider, { backgroundColor: colors.border }]} />
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

function CarouselSection({ title, items }: { title: string; items: Item[] }) {
  const { colors } = useTheme();
  const activeCount = items.filter(i => i.status === 'active').length;

  return (
    <View style={styles.section}>
      {/* Section header */}
      <View style={styles.sectionHeader}>
        <View style={styles.sectionLeft}>
          <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>{title}</Text>
          <View style={[styles.countPill, { backgroundColor: colors.surface, borderColor: colors.border }]}>
            <Text style={[styles.countText, { color: colors.textSecondary }]}>
              {activeCount} active
            </Text>
          </View>
        </View>
        <Text style={[styles.itemCount, { color: colors.textMuted }]}>
          {items.length} {items.length === 1 ? 'agent' : 'agents'}
        </Text>
      </View>

      {/* Carousel */}
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.carousel}
        decelerationRate="fast"
        snapToInterval={CARD_WIDTH + 10}
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

      {/* Add new agent — always visible below carousel */}
      <View style={styles.addNewRow}>
        <AddNewCard cardWidth={SCREEN_WIDTH - 40} onPress={() => {}} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },

  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingTop: 12,
    paddingBottom: 14,
    borderBottomWidth: 1,
  },
  headerLeft: {
    gap: 6,
  },
  appName: {
    fontSize: 24,
    fontWeight: '800',
    letterSpacing: -0.5,
  },
  agentCounter: {
    alignSelf: 'flex-start',
    borderRadius: 20,
    borderWidth: 1,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  agentCounterText: {
    fontSize: 11,
    fontWeight: '600',
  },
  avatarBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarInitials: {
    fontSize: 14,
    fontWeight: '700',
    color: '#FFFFFF',
  },

  scroll: { flex: 1 },
  scrollContent: { paddingBottom: 48 },

  section: {
    paddingTop: 24,
  },

  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    marginBottom: 12,
  },
  sectionLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '700',
    letterSpacing: -0.3,
  },
  countPill: {
    borderRadius: 20,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderWidth: 1,
  },
  countText: {
    fontSize: 11,
    fontWeight: '600',
  },
  itemCount: {
    fontSize: 12,
  },

  carousel: {
    paddingHorizontal: 20,
    gap: 10,
    paddingBottom: 4,
  },

  addNewRow: {
    paddingHorizontal: 20,
    marginTop: 10,
  },

  // Profile menu modal
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.4)',
    justifyContent: 'flex-start',
    alignItems: 'flex-end',
    paddingTop: 80,
    paddingRight: 16,
  },
  profileMenu: {
    width: 220,
    borderRadius: 14,
    borderWidth: 1,
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
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
  },
  profileMenuAvatarText: {
    fontSize: 13,
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
