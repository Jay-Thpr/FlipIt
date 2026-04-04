import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useTheme } from '../contexts/ThemeContext';
import { Item } from '../data/mockData';
import PlatformBadge from './PlatformBadge';

interface Props {
  item: Item;
  cardWidth: number;
  onPress: () => void;
}

const STATUS_LABEL: Record<string, string> = {
  active: 'Active',
  paused: 'Paused',
  archived: 'Archived',
};

const STATUS_DOT: Record<string, string> = {
  active: '#4ADE80',
  paused: '#A1A1AA',
  archived: '#F87171',
};

export default function ItemCard({ item, cardWidth, onPress }: Props) {
  const { colors } = useTheme();
  const cardHeight = Math.round(cardWidth / 0.68);

  const priceDisplay =
    item.minPrice && item.maxPrice
      ? `$${item.minPrice}–$${item.maxPrice}`
      : `$${item.targetPrice}`;

  const hasUnread = item.conversations.some(c => c.unread);

  return (
    <TouchableOpacity
      style={[styles.card, { width: cardWidth, height: cardHeight, borderColor: colors.border }]}
      onPress={onPress}
      activeOpacity={0.88}
    >
      {/* Background — colored image placeholder */}
      <View style={[StyleSheet.absoluteFill, { backgroundColor: item.imageColor }]} />

      {/* Watermark initial */}
      <Text style={styles.watermark}>{item.name[0]}</Text>

      {/* Top-right: status pill */}
      <View style={styles.topRight}>
        <View style={styles.statusPill}>
          <View style={[styles.statusDot, { backgroundColor: STATUS_DOT[item.status] }]} />
          <Text style={styles.statusText}>{STATUS_LABEL[item.status]}</Text>
        </View>
      </View>

      {/* Top-left: unread badge */}
      {hasUnread && (
        <View style={[styles.unreadBadge, { backgroundColor: colors.primary }]} />
      )}

      {/* Bottom overlay */}
      <View style={styles.overlay}>
        <Text style={styles.overlayName} numberOfLines={2}>{item.name}</Text>
        <Text style={styles.overlayPrice}>{priceDisplay}</Text>
        <View style={styles.overlayPlatforms}>
          {item.platforms.slice(0, 3).map(p => (
            <PlatformBadge key={p} platform={p} />
          ))}
          {item.platforms.length > 3 && (
            <Text style={styles.morePlatforms}>+{item.platforms.length - 3}</Text>
          )}
        </View>
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: 16,
    overflow: 'hidden',
    borderWidth: 1,
  },
  watermark: {
    position: 'absolute',
    fontSize: 120,
    fontWeight: '900',
    color: 'rgba(255,255,255,0.12)',
    top: '10%',
    alignSelf: 'center',
  },

  // Status pill top-right
  topRight: {
    position: 'absolute',
    top: 10,
    right: 10,
  },
  statusPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    backgroundColor: 'rgba(0,0,0,0.45)',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 20,
  },
  statusDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  statusText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#FFFFFF',
    letterSpacing: 0.2,
  },

  // Unread indicator top-left
  unreadBadge: {
    position: 'absolute',
    top: 10,
    left: 10,
    width: 9,
    height: 9,
    borderRadius: 5,
    borderWidth: 1.5,
    borderColor: 'rgba(255,255,255,0.4)',
  },

  // Bottom text overlay
  overlay: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    backgroundColor: 'rgba(0,0,0,0.62)',
    paddingHorizontal: 11,
    paddingTop: 10,
    paddingBottom: 12,
    gap: 3,
  },
  overlayName: {
    fontSize: 13,
    fontWeight: '700',
    color: '#FFFFFF',
    lineHeight: 17,
    letterSpacing: -0.1,
  },
  overlayPrice: {
    fontSize: 15,
    fontWeight: '800',
    color: '#FFFFFF',
    letterSpacing: -0.3,
  },
  overlayPlatforms: {
    flexDirection: 'row',
    gap: 4,
    marginTop: 4,
    alignItems: 'center',
  },
  morePlatforms: {
    fontSize: 10,
    fontWeight: '600',
    color: 'rgba(255,255,255,0.6)',
  },
});
