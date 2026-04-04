import React, { useState } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity, Switch,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, router } from 'expo-router';
import { ArrowLeft, ChevronRight, TrendingUp, TrendingDown } from 'lucide-react-native';
import { useTheme } from '../../contexts/ThemeContext';
import { mockItems, MarketData, Conversation, Platform } from '../../data/mockData';
import StatusBadge from '../../components/StatusBadge';
import PlatformBadge from '../../components/PlatformBadge';

export default function ItemDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { colors } = useTheme();
  const item = mockItems.find(i => i.id === id);

  if (!item) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]}>
        <Text style={{ padding: 24, color: colors.textMuted }}>Item not found.</Text>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView
      style={[styles.container, { backgroundColor: colors.background }]}
      edges={['top', 'bottom']}
    >
      {/* Header */}
      <View style={[styles.header, { borderBottomColor: colors.border }]}>
        <TouchableOpacity
          onPress={() => router.back()}
          style={[styles.backBtn, { backgroundColor: colors.surface, borderColor: colors.border }]}
          hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
        >
          <ArrowLeft size={20} color={colors.textPrimary} />
        </TouchableOpacity>
        <Text style={[styles.headerTitle, { color: colors.textPrimary }]} numberOfLines={1}>
          {item.name}
        </Text>
        <StatusBadge status={item.status} size="md" />
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scrollContent}>
        {/* Hero */}
        <View style={[styles.heroImage, { backgroundColor: item.imageColor }]}>
          <Text style={styles.heroInitial}>{item.name[0]}</Text>
        </View>

        {/* Overview */}
        <SectionCard title="Overview">
          <Text style={[styles.itemName, { color: colors.textPrimary }]}>{item.name}</Text>
          <Text style={[styles.description, { color: colors.textSecondary }]}>
            {item.description}
          </Text>
          <View style={styles.metaRow}>
            <MetaChip label="Condition" value={item.condition} />
            <MetaChip label="Qty" value={`×${item.quantity}`} />
            <MetaChip label="Mode" value={item.type === 'buy' ? 'Buying' : 'Selling'} />
          </View>
        </SectionCard>

        {/* Settings */}
        <SectionCard title="Settings">
          <SettingRow label="Target Price" value={`$${item.targetPrice}`} />
          {item.minPrice != null && (
            <SettingRow label="Min Acceptable" value={`$${item.minPrice}`} />
          )}
          {item.maxPrice != null && (
            <SettingRow label="Max Acceptable" value={`$${item.maxPrice}`} />
          )}
          {item.autoAcceptThreshold != null && (
            <SettingRow label="Auto-Accept Below" value={`$${item.autoAcceptThreshold}`} />
          )}
          <SettingRow
            label="Negotiation Style"
            value={item.negotiationStyle.charAt(0).toUpperCase() + item.negotiationStyle.slice(1)}
          />
          <SettingRow
            label="Reply Tone"
            value={item.replyTone.charAt(0).toUpperCase() + item.replyTone.slice(1)}
          />
          <SettingRow label="Active Platforms" value={item.platforms.join(', ')} />
          <SettingToggle label="Auto-Relist" value={item.autoRelist} />
        </SectionCard>

        {/* Market Overview */}
        <View style={styles.sectionHeader}>
          <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Market Overview</Text>
        </View>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.marketScroll}
        >
          {item.marketData.map(md => (
            <MarketCard key={md.platform} data={md} />
          ))}
        </ScrollView>

        {/* Active Conversations */}
        <SectionCard title={`Active Conversations (${item.conversations.length})`}>
          {item.conversations.length === 0 ? (
            <Text style={[styles.emptyText, { color: colors.textMuted }]}>
              No active conversations yet.
            </Text>
          ) : (
            item.conversations.map((conv, idx) => (
              <React.Fragment key={conv.id}>
                {idx > 0 && <View style={[styles.convDivider, { backgroundColor: colors.border }]} />}
                <ConvRow
                  conv={conv}
                  onPress={() => router.push(`/chat/${conv.id}?itemId=${item.id}`)}
                />
              </React.Fragment>
            ))
          )}
        </SectionCard>
      </ScrollView>
    </SafeAreaView>
  );
}

// ─── Sub-components ────────────────────────────────────────────────────────────

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  const { colors } = useTheme();
  return (
    <View style={styles.sectionCard}>
      <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>{title}</Text>
      <View
        style={[
          styles.cardBody,
          { backgroundColor: colors.surface, borderColor: colors.border },
        ]}
      >
        {children}
      </View>
    </View>
  );
}

function MetaChip({ label, value }: { label: string; value: string }) {
  const { colors } = useTheme();
  return (
    <View style={[styles.metaChip, { backgroundColor: colors.muted }]}>
      <Text style={[styles.metaLabel, { color: colors.textMuted }]}>{label}</Text>
      <Text style={[styles.metaValue, { color: colors.textPrimary }]}>{value}</Text>
    </View>
  );
}

function SettingRow({ label, value }: { label: string; value: string }) {
  const { colors } = useTheme();
  return (
    <View style={[styles.settingRow, { borderBottomColor: colors.border }]}>
      <Text style={[styles.settingLabel, { color: colors.textPrimary }]}>{label}</Text>
      <Text style={[styles.settingValue, { color: colors.textSecondary }]}>{value}</Text>
    </View>
  );
}

function SettingToggle({ label, value }: { label: string; value: boolean }) {
  const { colors } = useTheme();
  const [val, setVal] = useState(value);
  return (
    <View style={[styles.settingRow, { borderBottomColor: 'transparent' }]}>
      <Text style={[styles.settingLabel, { color: colors.textPrimary }]}>{label}</Text>
      <Switch
        value={val}
        onValueChange={setVal}
        trackColor={{ true: colors.primary, false: colors.border }}
        thumbColor={colors.white}
      />
    </View>
  );
}

function MarketCard({ data }: { data: MarketData }) {
  const { colors } = useTheme();
  const isUp = data.trend >= 0;
  return (
    <View
      style={[
        styles.marketCard,
        { backgroundColor: colors.surface, borderColor: colors.border },
      ]}
    >
      <PlatformBadge platform={data.platform as Platform} size="md" />
      <Text style={[styles.marketPrice, { color: colors.textPrimary }]}>${data.price}</Text>
      <View style={styles.trendRow}>
        {isUp
          ? <TrendingUp size={12} color={colors.accent} />
          : <TrendingDown size={12} color={colors.destructive} />
        }
        <Text style={[styles.trendText, { color: isUp ? colors.accent : colors.destructive }]}>
          {isUp ? '+' : ''}{data.trend}%
        </Text>
      </View>
      <Text style={[styles.volumeText, { color: colors.textMuted }]}>{data.volume} listings</Text>
    </View>
  );
}

function ConvRow({ conv, onPress }: { conv: Conversation; onPress: () => void }) {
  const { colors } = useTheme();
  return (
    <TouchableOpacity style={styles.convRow} onPress={onPress} activeOpacity={0.7}>
      <PlatformBadge platform={conv.platform} size="md" />
      <View style={styles.convInfo}>
        <View style={styles.convNameRow}>
          <Text style={[styles.convUsername, { color: colors.textPrimary }]}>
            {conv.username}
          </Text>
          {conv.unread && (
            <View style={[styles.unreadDot, { backgroundColor: colors.primary }]} />
          )}
        </View>
        <Text style={[styles.convPreview, { color: colors.textMuted }]} numberOfLines={1}>
          {conv.lastMessage}
        </Text>
      </View>
      <View style={styles.convRight}>
        <Text style={[styles.convTime, { color: colors.textMuted }]}>{conv.timestamp}</Text>
        <ChevronRight size={16} color={colors.textMuted} />
      </View>
    </TouchableOpacity>
  );
}

// ─── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    gap: 10,
    borderBottomWidth: 1,
  },
  backBtn: {
    width: 38,
    height: 38,
    borderRadius: 10,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerTitle: {
    flex: 1,
    fontSize: 16,
    fontWeight: '700',
  },
  scrollContent: { paddingBottom: 48 },

  heroImage: {
    width: '100%',
    height: 200,
    alignItems: 'center',
    justifyContent: 'center',
  },
  heroInitial: {
    fontSize: 72,
    fontWeight: '800',
    color: 'rgba(255,255,255,0.75)',
  },

  sectionCard: {
    marginHorizontal: 16,
    marginTop: 20,
  },
  sectionHeader: {
    paddingHorizontal: 16,
    marginTop: 20,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '700',
    letterSpacing: 0.1,
    marginBottom: 10,
  },
  cardBody: {
    borderRadius: 14,
    borderWidth: 1,
    overflow: 'hidden',
  },

  itemName: {
    fontSize: 18,
    fontWeight: '700',
    marginBottom: 6,
    paddingHorizontal: 14,
    paddingTop: 14,
  },
  description: {
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 12,
    paddingHorizontal: 14,
  },
  metaRow: {
    flexDirection: 'row',
    gap: 8,
    paddingHorizontal: 14,
    paddingBottom: 14,
  },
  metaChip: {
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 5,
    alignItems: 'center',
  },
  metaLabel: {
    fontSize: 10,
    fontWeight: '500',
  },
  metaValue: {
    fontSize: 13,
    fontWeight: '700',
  },

  settingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 14,
    paddingVertical: 13,
    borderBottomWidth: 1,
  },
  settingLabel: {
    fontSize: 14,
    fontWeight: '500',
  },
  settingValue: {
    fontSize: 14,
    fontWeight: '400',
  },

  marketScroll: {
    paddingHorizontal: 16,
    gap: 10,
  },
  marketCard: {
    borderRadius: 12,
    borderWidth: 1,
    padding: 14,
    minWidth: 110,
    gap: 4,
  },
  marketPrice: {
    fontSize: 22,
    fontWeight: '800',
    marginTop: 6,
  },
  trendRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
  },
  trendText: {
    fontSize: 12,
    fontWeight: '600',
  },
  volumeText: {
    fontSize: 11,
    marginTop: 2,
  },

  emptyText: {
    fontSize: 14,
    textAlign: 'center',
    paddingVertical: 20,
  },
  convRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 14,
    paddingVertical: 12,
    gap: 10,
  },
  convDivider: {
    height: 1,
    marginHorizontal: 14,
  },
  convInfo: {
    flex: 1,
    gap: 3,
  },
  convNameRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  convUsername: {
    fontSize: 14,
    fontWeight: '600',
  },
  unreadDot: {
    width: 7,
    height: 7,
    borderRadius: 4,
  },
  convPreview: {
    fontSize: 13,
  },
  convRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  convTime: {
    fontSize: 11,
  },
});
