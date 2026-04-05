import { View, Text, Image, StyleSheet, TouchableOpacity } from 'react-native';
import { useTheme } from '../contexts/ThemeContext';
import { Item } from '../data/mockData';

interface Props {
  item: Item;
  cardWidth: number;
  onPress: () => void;
}

export default function ItemCard({ item, cardWidth, onPress }: Props) {
  const { colors, isDark } = useTheme();

  const offerDisplay = item.bestOffer
    ? `$${item.bestOffer}`
    : 'None';

  const statusLabel = item.status === 'active' ? 'Active' : 'Paused';
  const statusColor = item.status === 'active' ? colors.accent : colors.destructive;
  const hasPhoto = item.photos.length > 0;
  const imageHeight = Math.round(cardWidth * 0.6);

  return (
    <TouchableOpacity
      style={[
        styles.card,
        {
          width: cardWidth,
          backgroundColor: colors.surface,
        },
      ]}
      onPress={onPress}
      activeOpacity={0.7}
    >
      {/* Photo preview or colored placeholder */}
      <View style={[styles.imageContainer, { height: imageHeight }]}>
        {hasPhoto ? (
          <Image
            source={{ uri: item.photos[0] }}
            style={styles.image}
            resizeMode="cover"
          />
        ) : (
          <View style={[styles.imagePlaceholder, { backgroundColor: item.imageColor }]}>
            <Text style={styles.placeholderInitial}>{item.name[0]}</Text>
          </View>
        )}
        {/* Status label over image */}
        <View style={styles.statusOverlay}>
          <Text style={[styles.statusOverlayText, { color: statusColor }]}>{statusLabel}</Text>
        </View>
      </View>

      {/* Content below image */}
      <View style={styles.content}>
        {/* Item name */}
        <Text style={[styles.name, { color: colors.textPrimary }]} numberOfLines={2}>
          {item.name}
        </Text>

        {/* Bottom row: offer + target */}
        <View style={styles.bottomRow}>
          <View>
            <Text style={[styles.priceLabel, { color: colors.textMuted }]}>Best Offer</Text>
            <Text style={[styles.priceValue, { color: item.bestOffer ? colors.accent : colors.textPrimary }]}>
              {offerDisplay}
            </Text>
          </View>
          <View style={styles.targetBlock}>
            <Text style={[styles.priceLabel, { color: colors.textMuted }]}>Target</Text>
            <Text style={[styles.targetValue, { color: colors.textPrimary }]}>
              ${item.targetPrice}
            </Text>
          </View>
        </View>
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: 12,
    overflow: 'hidden',
  },

  imageContainer: {
    width: '100%',
    overflow: 'hidden',
  },
  image: {
    width: '100%',
    height: '100%',
  },
  imagePlaceholder: {
    width: '100%',
    height: '100%',
    alignItems: 'center',
    justifyContent: 'center',
  },
  placeholderInitial: {
    fontSize: 48,
    fontWeight: '800',
    color: 'rgba(255,255,255,0.5)',
  },
  statusOverlay: {
    position: 'absolute',
    top: 8,
    left: 8,
    backgroundColor: 'rgba(0,0,0,0.5)',
    borderRadius: 4,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  statusOverlayText: {
    fontSize: 10,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.4,
  },

  content: {
    padding: 14,
    gap: 10,
  },

  name: {
    fontSize: 15,
    fontWeight: '700',
    letterSpacing: -0.2,
    lineHeight: 20,
  },

  bottomRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    justifyContent: 'space-between',
    marginTop: 2,
  },
  priceLabel: {
    fontSize: 10,
    fontWeight: '500',
    textTransform: 'uppercase',
    letterSpacing: 0.4,
    marginBottom: 2,
  },
  priceValue: {
    fontSize: 18,
    fontWeight: '800',
    letterSpacing: -0.3,
    fontVariant: ['tabular-nums'],
  },
  targetBlock: {
    alignItems: 'flex-end',
  },
  targetValue: {
    fontSize: 15,
    fontWeight: '600',
    letterSpacing: -0.2,
    fontVariant: ['tabular-nums'],
  },
});
