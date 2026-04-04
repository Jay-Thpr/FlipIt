import React, { useState } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity, Switch, Alert,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, router } from 'expo-router';
import { ArrowLeft, ChevronRight } from 'lucide-react-native';
import { useTheme } from '../../contexts/ThemeContext';
import { mockItems, MarketData, Conversation, PLATFORM_NAMES } from '../../data/mockData';
import StatusBadge from '../../components/StatusBadge';

export default function ItemDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { colors } = useTheme();
  const item = mockItems.find(i => i.id === id);
  const [aiActive, setAiActive] = useState(item?.status === 'active');

  if (!item) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]}>
        <Text style={{ padding: 24, color: colors.textMuted }}>Item not found.</Text>
      </SafeAreaView>
    );
  }

  function handleArchive() {
    Alert.alert(
      'Archive Listing',
      'Are you sure you want to archive this listing? The AI agent will stop and it will be removed from active agents.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Archive',
          style: 'destructive',
          onPress: () => router.back(),
        },
      ]
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
          style={styles.backBtn}
          hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
        >
          <ArrowLeft size={22} color={colors.textPrimary} />
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
          <InfoRow label="Description" value={item.description} />
          <InfoDivider />
          <InfoRow label="Condition" value={item.condition} />
          <InfoDivider />
          <InfoRow label="Quantity" value={`×${item.quantity}`} />
          <InfoDivider />
          <InfoRow label="Mode" value={item.type === 'buy' ? 'Buying' : 'Selling'} />
          {item.bestOffer != null && (
            <>
              <InfoDivider />
              <InfoRow label="Best Current Offer" value={`$${item.bestOffer}`} highlight />
            </>
          )}
        </SectionCard>

        {/* Settings */}
        <SectionCard title="Settings">
          {/* AI Agent toggle */}
          <SettingToggle
            label="AI Agent Active"
            value={aiActive}
            onToggle={() => setAiActive(v => !v)}
          />
          <SettingDivider />
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
          <SettingRow label="Active Platforms" value={item.platforms.map(p => PLATFORM_NAMES[p]).join(', ')} />
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

        {/* Archive */}
        <View style={styles.dangerZone}>
          <TouchableOpacity
            style={[styles.archiveBtn, { borderColor: colors.destructive }]}
            onPress={handleArchive}
            activeOpacity={0.7}
          >
            <Text style={[styles.archiveBtnText, { color: colors.destructive }]}>
              Archive Listing
            </Text>
          </TouchableOpacity>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

// ─── Sub-components ────────────────────────────────────────────────────────────

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  const { colors } = useTheme();
  return (
    <View style={styles.sectionCard}>
      <Text style={[styles.sectionLabel, { color: colors.textMuted }]}>{title.toUpperCase()}</Text>
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

function InfoDivider() {
  const { colors } = useTheme();
  return <View style={[styles.infoDivider, { backgroundColor: colors.border }]} />;
}

function InfoRow({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  const { colors } = useTheme();
  return (
    <View style={styles.infoRow}>
      <Text style={[styles.infoLabel, { color: colors.textMuted }]}>{label}</Text>
      <Text
        style={[
          styles.infoValue,
          { color: highlight ? colors.primary : colors.textPrimary },
          highlight && styles.infoValueHighlight,
        ]}
      >
        {value}
      </Text>
    </View>
  );
}

function SettingDivider() {
  const { colors } = useTheme();
  return <View style={[styles.settingDivider, { backgroundColor: colors.border }]} />;
}

function SettingRow({ label, value }: { label: string; value: string }) {
  const { colors } = useTheme();
  return (
    <View style={styles.settingRow}>
      <Text style={[styles.settingLabel, { color: colors.textPrimary }]}>{label}</Text>
      <Text style={[styles.settingValue, { color: colors.textSecondary }]}>{value}</Text>
    </View>
  );
}

function SettingToggle({ label, value, onToggle }: { label: string; value: boolean; onToggle: () => void }) {
  const { colors } = useTheme();
  return (
    <View style={styles.settingRow}>
      <Text style={[styles.settingLabel, { color: colors.textPrimary }]}>{label}</Text>
      <Switch
        value={value}
        onValueChange={onToggle}
        trackColor={{ true: colors.primary, false: colors.border }}
        thumbColor={colors.white}
      />
    </View>
  );
}

function MarketCard({ data }: { data: MarketData }) {
  const { colors } = useTheme();
  const platformName = PLATFORM_NAMES[data.platform];
  return (
    <View
      style={[
        styles.marketCard,
        { backgroundColor: colors.surface, borderColor: colors.border },
      ]}
    >
      <Text style={[styles.marketName, { color: colors.textPrimary }]}>{platformName}</Text>
      <View style={styles.marketPriceRow}>
        <View>
          <Text style={[styles.marketPriceLabel, { color: colors.textMuted }]}>Buy</Text>
          <Text style={[styles.marketPrice, { color: colors.accent }]}>${data.bestBuyPrice}</Text>
        </View>
        <View style={[styles.marketDivider, { backgroundColor: colors.border }]} />
        <View>
          <Text style={[styles.marketPriceLabel, { color: colors.textMuted }]}>Sell</Text>
          <Text style={[styles.marketPrice, { color: colors.textPrimary }]}>${data.bestSellPrice}</Text>
        </View>
      </View>
      <Text style={[styles.volumeText, { color: colors.textMuted }]}>{data.volume} listings</Text>
    </View>
  );
}

function ConvRow({ conv, onPress }: { conv: Conversation; onPress: () => void }) {
  const { colors } = useTheme();
  return (
    <TouchableOpacity style={styles.convRow} onPress={onPress} activeOpacity={0.7}>
      <View style={styles.convInfo}>
        <View style={styles.convNameRow}>
          <Text style={[styles.convUsername, { color: colors.textPrimary }]}>
            {conv.username}
          </Text>
          <Text style={[styles.convPlatform, { color: colors.textMuted }]}>
            {PLATFORM_NAMES[conv.platform]}
          </Text>
        </View>
        <Text
          style={[
            styles.convPreview,
            { color: conv.unread ? colors.textPrimary : colors.textMuted },
            conv.unread && styles.convPreviewUnread,
          ]}
          numberOfLines={1}
        >
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
    width: 36,
    height: 36,
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
  sectionLabel: {
    fontSize: 11,
    fontWeight: '600',
    letterSpacing: 0.8,
    marginBottom: 8,
    paddingHorizontal: 4,
  },
  sectionHeader: {
    paddingHorizontal: 16,
    marginTop: 20,
    marginBottom: 0,
  },
  sectionTitle: {
    fontSize: 11,
    fontWeight: '600',
    letterSpacing: 0.8,
    textTransform: 'uppercase',
    marginBottom: 8,
    paddingHorizontal: 4,
  },
  cardBody: {
    borderRadius: 14,
    borderWidth: 1,
    overflow: 'hidden',
  },

  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    paddingHorizontal: 14,
    paddingVertical: 11,
    gap: 12,
  },
  infoDivider: { height: 1 },
  infoLabel: {
    fontSize: 14,
    fontWeight: '500',
    flex: 1,
  },
  infoValue: {
    fontSize: 14,
    flex: 2,
    textAlign: 'right',
  },
  infoValueHighlight: {
    fontWeight: '700',
  },

  settingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 14,
    paddingVertical: 13,
  },
  settingDivider: { height: 1 },
  settingLabel: {
    fontSize: 14,
    fontWeight: '500',
  },
  settingValue: {
    fontSize: 14,
    fontWeight: '400',
    maxWidth: '55%',
    textAlign: 'right',
  },

  marketScroll: {
    paddingHorizontal: 16,
    gap: 10,
    paddingBottom: 4,
  },
  marketCard: {
    borderRadius: 12,
    borderWidth: 1,
    padding: 14,
    minWidth: 120,
    gap: 8,
  },
  marketName: {
    fontSize: 13,
    fontWeight: '700',
  },
  marketPriceRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  marketDivider: {
    width: 1,
    height: 32,
  },
  marketPriceLabel: {
    fontSize: 10,
    fontWeight: '500',
    marginBottom: 2,
  },
  marketPrice: {
    fontSize: 18,
    fontWeight: '800',
    letterSpacing: -0.3,
  },
  volumeText: {
    fontSize: 11,
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
  convPlatform: {
    fontSize: 12,
  },
  convPreview: {
    fontSize: 13,
  },
  convPreviewUnread: {
    fontWeight: '500',
  },
  convRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  convTime: {
    fontSize: 11,
  },

  dangerZone: {
    marginHorizontal: 16,
    marginTop: 32,
  },
  archiveBtn: {
    borderWidth: 1,
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
  },
  archiveBtnText: {
    fontSize: 15,
    fontWeight: '600',
  },
});
