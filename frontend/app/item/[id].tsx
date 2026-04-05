import React, { useState } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity, Switch, Alert, Image,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, router } from 'expo-router';
import { ArrowLeft, ChevronRight, ChevronLeft, Plus, X } from 'lucide-react-native';
import { useTheme } from '../../contexts/ThemeContext';
import { mockItems, MarketData, Conversation, PLATFORM_NAMES } from '../../data/mockData';
import StatusBadge from '../../components/StatusBadge';

export default function ItemDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { colors, isDark } = useTheme();
  const item = mockItems.find(i => i.id === id);
  const [aiActive, setAiActive] = useState(item?.status === 'active');
  const [photos, setPhotos] = useState<string[]>(item?.photos ?? []);

  if (!item) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]}>
        <Text style={{ padding: 24, color: colors.textMuted }}>Item not found.</Text>
      </SafeAreaView>
    );
  }

  function movePhoto(index: number, direction: 'up' | 'down') {
    const newPhotos = [...photos];
    const targetIndex = direction === 'up' ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= newPhotos.length) return;
    [newPhotos[index], newPhotos[targetIndex]] = [newPhotos[targetIndex], newPhotos[index]];
    setPhotos(newPhotos);
  }

  function removePhoto(index: number) {
    Alert.alert('Remove Photo', 'Are you sure you want to remove this photo?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Remove', style: 'destructive', onPress: () => setPhotos(p => p.filter((_, i) => i !== index)) },
    ]);
  }

  function handleAddPhoto() {
    // Placeholder — would use expo-image-picker in production
    Alert.alert('Add Photo', 'Image picker would open here. (Not wired to a real picker yet.)');
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
      <View style={styles.header}>
        <TouchableOpacity
          onPress={() => router.back()}
          style={styles.backBtn}
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
        {/* Hero — compact colored strip with key metrics */}
        <View style={[styles.heroStrip, { backgroundColor: colors.surface }]}>
          <View style={[styles.heroAccent, { backgroundColor: isDark ? colors.primary : colors.muted }]} />
          <View style={styles.heroContent}>
            <View style={styles.heroMetric}>
              <Text style={[styles.heroMetricLabel, { color: colors.textMuted }]}>BEST OFFER</Text>
              <Text style={[styles.heroMetricValue, { color: item.bestOffer ? colors.accent : colors.textPrimary }]}>
                {item.bestOffer ? `$${item.bestOffer}` : 'None'}
              </Text>
            </View>
            <View style={[styles.heroDivider, { backgroundColor: colors.divider }]} />
            <View style={styles.heroMetric}>
              <Text style={[styles.heroMetricLabel, { color: colors.textMuted }]}>TARGET</Text>
              <Text style={[styles.heroMetricValue, { color: colors.textPrimary }]}>
                ${item.targetPrice}
              </Text>
            </View>
            <View style={[styles.heroDivider, { backgroundColor: colors.divider }]} />
            <View style={styles.heroMetric}>
              <Text style={[styles.heroMetricLabel, { color: colors.textMuted }]}>MODE</Text>
              <Text style={[styles.heroMetricValue, { color: colors.primary }]}>
                {item.type === 'buy' ? 'Buy' : 'Sell'}
              </Text>
            </View>
          </View>
        </View>

        {/* Photos — scrollable gallery with reorder + delete */}
        <View style={styles.sectionCard}>
          <View style={styles.photoHeaderRow}>
            <Text style={[styles.sectionLabel, { color: colors.textMuted, marginBottom: 0 }]}>
              PHOTOS ({photos.length})
            </Text>
            <TouchableOpacity
              style={[styles.addPhotoBtn, { backgroundColor: colors.surfaceRaised }]}
              onPress={handleAddPhoto}
              hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
              accessibilityLabel="Add photo"
            >
              <Plus size={16} color={colors.primary} />
              <Text style={[styles.addPhotoBtnText, { color: colors.primary }]}>Add</Text>
            </TouchableOpacity>
          </View>
          {photos.length === 0 ? (
            <TouchableOpacity
              style={[styles.emptyPhotos, { backgroundColor: colors.surface }]}
              onPress={handleAddPhoto}
              activeOpacity={0.7}
            >
              <Plus size={24} color={colors.textMuted} />
              <Text style={[styles.emptyPhotosText, { color: colors.textMuted }]}>
                Add photos for your listing
              </Text>
              <Text style={[styles.emptyPhotosHint, { color: colors.textMuted }]}>
                Photos are uploaded in order when the AI creates listings
              </Text>
            </TouchableOpacity>
          ) : (
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.photoScroll}
            >
              {photos.map((uri, idx) => (
                <View key={`${uri}-${idx}`} style={[styles.photoCard, { backgroundColor: colors.surface }]}>
                  <View style={styles.photoImageWrap}>
                    <Image source={{ uri }} style={styles.photoImage} resizeMode="cover" />
                    {/* Position badge */}
                    <View style={styles.photoBadge}>
                      <Text style={styles.photoBadgeText}>{idx + 1}</Text>
                    </View>
                    {/* Delete button — large, top-right */}
                    <TouchableOpacity
                      style={styles.photoDeleteBtn}
                      onPress={() => removePhoto(idx)}
                      hitSlop={{ top: 4, bottom: 4, left: 4, right: 4 }}
                      accessibilityLabel="Remove photo"
                    >
                      <X size={14} color="#FFFFFF" />
                    </TouchableOpacity>
                  </View>
                  {/* Reorder arrows — large touch targets */}
                  <View style={styles.photoReorderRow}>
                    <TouchableOpacity
                      onPress={() => movePhoto(idx, 'up')}
                      disabled={idx === 0}
                      style={[
                        styles.reorderBtn,
                        { backgroundColor: colors.surfaceRaised, opacity: idx === 0 ? 0.3 : 1 },
                      ]}
                      hitSlop={{ top: 4, bottom: 4, left: 4, right: 4 }}
                      accessibilityLabel="Move left"
                    >
                      <ChevronLeft size={16} color={colors.textSecondary} />
                    </TouchableOpacity>
                    <TouchableOpacity
                      onPress={() => movePhoto(idx, 'down')}
                      disabled={idx === photos.length - 1}
                      style={[
                        styles.reorderBtn,
                        { backgroundColor: colors.surfaceRaised, opacity: idx === photos.length - 1 ? 0.3 : 1 },
                      ]}
                      hitSlop={{ top: 4, bottom: 4, left: 4, right: 4 }}
                      accessibilityLabel="Move right"
                    >
                      <ChevronRight size={16} color={colors.textSecondary} />
                    </TouchableOpacity>
                  </View>
                </View>
              ))}
            </ScrollView>
          )}
        </View>

        {/* AI Agent toggle — below photos */}
        <View style={[styles.aiToggleRow, { backgroundColor: colors.surface }]}>
          <Text style={[styles.aiToggleLabel, { color: colors.textPrimary }]}>AI Agent Active</Text>
          <Switch
            value={aiActive}
            onValueChange={() => setAiActive(v => !v)}
            trackColor={{ true: colors.primary, false: colors.muted }}
            thumbColor={colors.white}
          />
        </View>

        {/* Overview — description stacked vertically, then compact rows */}
        <SectionCard title="Overview">
          <View style={styles.descriptionBlock}>
            <Text style={[styles.descriptionLabel, { color: colors.textMuted }]}>Description</Text>
            <Text style={[styles.descriptionValue, { color: colors.textPrimary }]}>{item.description}</Text>
          </View>
          <View style={[styles.infoDivider, { backgroundColor: colors.divider }]} />
          <View style={styles.compactRow}>
            <View style={styles.compactItem}>
              <Text style={[styles.compactLabel, { color: colors.textMuted }]}>Condition</Text>
              <Text style={[styles.compactValue, { color: colors.textPrimary }]}>{item.condition}</Text>
            </View>
            <View style={styles.compactItem}>
              <Text style={[styles.compactLabel, { color: colors.textMuted }]}>Quantity</Text>
              <Text style={[styles.compactValue, { color: colors.textPrimary }]}>{item.quantity}</Text>
            </View>
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
          <SettingRow label="Active Platforms" value={item.platforms.map(p => PLATFORM_NAMES[p]).join(', ')} />
        </SectionCard>

        {/* Market Overview */}
        <View style={styles.sectionHeader}>
          <Text style={[styles.sectionTitle, { color: colors.textMuted }]}>Market Overview</Text>
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
                {idx > 0 && <View style={[styles.convDivider, { backgroundColor: colors.divider }]} />}
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
            style={[styles.archiveBtn, { backgroundColor: colors.surface }]}
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
      <View style={[styles.cardBody, { backgroundColor: colors.surface }]}>
        {children}
      </View>
    </View>
  );
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

function MarketCard({ data }: { data: MarketData }) {
  const { colors } = useTheme();
  const platformName = PLATFORM_NAMES[data.platform];
  return (
    <View style={[styles.marketCard, { backgroundColor: colors.surface }]}>
      <Text style={[styles.marketName, { color: colors.textPrimary }]}>{platformName}</Text>
      <View style={styles.marketPriceRow}>
        <View>
          <Text style={[styles.marketPriceLabel, { color: colors.textMuted }]}>Buy</Text>
          <Text style={[styles.marketPrice, { color: colors.accent }]}>${data.bestBuyPrice}</Text>
        </View>
        <View style={[styles.marketDivider, { backgroundColor: colors.divider }]} />
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
        {/* #9: highlight timestamp when unread */}
        <Text style={[
          styles.convTime,
          { color: conv.unread ? colors.textPrimary : colors.textMuted },
          conv.unread && styles.convTimeUnread,
        ]}>
          {conv.timestamp}
        </Text>
        <ChevronRight size={14} color={colors.textMuted} />
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
    letterSpacing: -0.2,
  },
  scrollContent: { paddingBottom: 48 },

  // Hero strip
  heroStrip: {
    overflow: 'hidden',
  },
  heroAccent: {
    height: 3,
    width: '100%',
  },
  heroContent: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 16,
    paddingHorizontal: 16,
  },
  heroMetric: {
    flex: 1,
    alignItems: 'center',
    gap: 4,
  },
  heroMetricLabel: {
    fontSize: 10,
    fontWeight: '600',
    letterSpacing: 0.6,
  },
  heroMetricValue: {
    fontSize: 20,
    fontWeight: '800',
    letterSpacing: -0.3,
    fontVariant: ['tabular-nums'],
  },
  heroDivider: {
    width: 1,
    height: 36,
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
    borderRadius: 12,
    overflow: 'hidden',
  },

  // Overview — stacked description (#7)
  descriptionBlock: {
    paddingHorizontal: 14,
    paddingVertical: 12,
    gap: 6,
  },
  descriptionLabel: {
    fontSize: 11,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.4,
  },
  descriptionValue: {
    fontSize: 14,
    lineHeight: 20,
  },
  infoDivider: { height: 1 },
  compactRow: {
    flexDirection: 'row',
    paddingHorizontal: 14,
    paddingVertical: 12,
    gap: 16,
  },
  compactItem: {
    flex: 1,
    gap: 4,
  },
  compactLabel: {
    fontSize: 11,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.4,
  },
  compactValue: {
    fontSize: 14,
    fontWeight: '600',
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
    fontVariant: ['tabular-nums'],
  },

  marketScroll: {
    paddingHorizontal: 16,
    gap: 10,
    paddingBottom: 4,
  },
  marketCard: {
    borderRadius: 12,
    padding: 14,
    minWidth: 130,
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
    fontWeight: '600',
    letterSpacing: 0.4,
    textTransform: 'uppercase',
    marginBottom: 2,
  },
  marketPrice: {
    fontSize: 18,
    fontWeight: '800',
    letterSpacing: -0.3,
    fontVariant: ['tabular-nums'],
  },
  volumeText: {
    fontSize: 11,
    fontWeight: '500',
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
    fontVariant: ['tabular-nums'],
  },
  convTimeUnread: {
    fontWeight: '600',
  },

  // AI Agent toggle
  aiToggleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginHorizontal: 16,
    marginTop: 12,
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 13,
  },
  aiToggleLabel: {
    fontSize: 15,
    fontWeight: '600',
  },

  // Photos
  photoHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 4,
    marginBottom: 8,
  },
  addPhotoBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    borderRadius: 6,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
  addPhotoBtnText: {
    fontSize: 13,
    fontWeight: '600',
  },
  emptyPhotos: {
    borderRadius: 12,
    paddingVertical: 32,
    alignItems: 'center',
    gap: 8,
  },
  emptyPhotosText: {
    fontSize: 14,
    fontWeight: '500',
  },
  emptyPhotosHint: {
    fontSize: 12,
    textAlign: 'center',
    paddingHorizontal: 32,
  },
  photoScroll: {
    gap: 12,
    paddingBottom: 4,
  },
  photoCard: {
    borderRadius: 12,
    overflow: 'hidden',
    width: 150,
  },
  photoImageWrap: {
    width: 150,
    height: 150,
    position: 'relative',
  },
  photoImage: {
    width: 150,
    height: 150,
  },
  photoBadge: {
    position: 'absolute',
    bottom: 6,
    left: 6,
    backgroundColor: 'rgba(0,0,0,0.6)',
    borderRadius: 4,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  photoBadgeText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#FFFFFF',
    fontVariant: ['tabular-nums'],
  },
  photoDeleteBtn: {
    position: 'absolute',
    top: 6,
    right: 6,
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: 'rgba(0,0,0,0.6)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  photoReorderRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 8,
  },
  reorderBtn: {
    width: 36,
    height: 32,
    borderRadius: 6,
    alignItems: 'center',
    justifyContent: 'center',
  },
  addPhotoCard: {
    borderRadius: 12,
    width: 150,
    height: 190,
    alignItems: 'center',
    justifyContent: 'center',
  },

  dangerZone: {
    marginHorizontal: 16,
    marginTop: 32,
  },
  archiveBtn: {
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
  },
  archiveBtnText: {
    fontSize: 15,
    fontWeight: '600',
  },
});
