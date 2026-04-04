import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Plus } from 'lucide-react-native';
import { useTheme } from '../contexts/ThemeContext';

interface Props {
  cardWidth: number;
  onPress: () => void;
}

export default function AddNewCard({ cardWidth, onPress }: Props) {
  const { colors } = useTheme();
  const cardHeight = Math.round(cardWidth / 0.68);

  return (
    <TouchableOpacity
      style={[
        styles.card,
        {
          width: cardWidth,
          height: cardHeight,
          borderColor: colors.border,
          backgroundColor: colors.surface,
        },
      ]}
      onPress={onPress}
      activeOpacity={0.7}
    >
      <View style={[styles.iconCircle, { backgroundColor: colors.muted, borderColor: colors.border }]}>
        <Plus size={22} color={colors.primary} />
      </View>
      <Text style={[styles.label, { color: colors.textSecondary }]}>Add New</Text>
      <Text style={[styles.hint, { color: colors.textMuted }]}>Set up an agent</Text>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: 16,
    borderWidth: 1,
    borderStyle: 'dashed',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
  },
  iconCircle: {
    width: 48,
    height: 48,
    borderRadius: 24,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 2,
  },
  label: {
    fontSize: 14,
    fontWeight: '600',
  },
  hint: {
    fontSize: 11,
  },
});
