import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useTheme } from '../contexts/ThemeContext';
import { Item } from '../data/mockData';

interface Props {
  item: Item;
  cardWidth: number;
  onPress: () => void;
}

const STATUS_TEXT_COLOR: Record<string, string> = {
  active: '#4ADE80',
  paused: '#A1A1AA',
  archived: '#A1A1AA',
};

export default function ItemCard({ item, cardWidth, onPress }: Props) {
  const { colors } = useTheme();
  const cardHeight = Math.round(cardWidth / 0.68);

  const offerDisplay = item.bestOffer
    ? `$${item.bestOffer}`
    : 'Finding...';

  const statusLabel = item.status === 'active' ? 'Active' : 'Paused';
  const statusColor = STATUS_TEXT_COLOR[item.status] ?? '#A1A1AA';

  return (
    <TouchableOpacity
      style={[styles.card, { width: cardWidth, height: cardHeight, borderColor: colors.border }]}
      onPress={onPress}
      activeOpacity={0.88}
    >
      {/* Background */}
      <View style={[StyleSheet.absoluteFill, { backgroundColor: item.imageColor }]} />

      {/* Watermark initial */}
      <Text style={styles.watermark}>{item.name[0]}</Text>

      {/* Top-left: status text label */}
      <View style={styles.topLeft}>
        <Text style={[styles.statusLabel, { color: statusColor }]}>{statusLabel}</Text>
      </View>

      {/* Bottom overlay */}
      <View style={styles.overlay}>
        <Text style={styles.overlayName} numberOfLines={2}>{item.name}</Text>
        <Text style={styles.overlayOffer}>{offerDisplay}</Text>
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

  topLeft: {
    position: 'absolute',
    top: 10,
    left: 10,
  },
  statusLabel: {
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.2,
    textShadowColor: 'rgba(0,0,0,0.5)',
    textShadowOffset: { width: 0, height: 1 },
    textShadowRadius: 2,
  },

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
  overlayOffer: {
    fontSize: 15,
    fontWeight: '800',
    color: '#FFFFFF',
    letterSpacing: -0.3,
  },
});
