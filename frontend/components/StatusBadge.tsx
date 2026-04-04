import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '../contexts/ThemeContext';
import { ItemStatus } from '../data/mockData';

interface Props {
  status: ItemStatus;
  size?: 'sm' | 'md';
}

export default function StatusBadge({ status, size = 'sm' }: Props) {
  const { isDark } = useTheme();

  const CONFIG: Record<ItemStatus, { bg: string; text: string; label: string }> = isDark
    ? {
        active:   { bg: '#052E16', text: '#4ADE80', label: 'Active' },
        paused:   { bg: '#27272A', text: '#A1A1AA', label: 'Paused' },
        archived: { bg: '#450A0A', text: '#F87171', label: 'Archived' },
      }
    : {
        active:   { bg: '#DCFCE7', text: '#15803D', label: 'Active' },
        paused:   { bg: '#F4F4F5', text: '#71717A', label: 'Paused' },
        archived: { bg: '#FEE2E2', text: '#DC2626', label: 'Archived' },
      };

  const cfg = CONFIG[status];
  return (
    <View style={[styles.badge, { backgroundColor: cfg.bg }, size === 'md' && styles.badgeMd]}>
      <Text style={[styles.text, { color: cfg.text }, size === 'md' && styles.textMd]}>
        {cfg.label}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    paddingHorizontal: 7,
    paddingVertical: 3,
    borderRadius: 20,
  },
  badgeMd: {
    paddingHorizontal: 12,
    paddingVertical: 5,
  },
  text: {
    fontSize: 10,
    fontWeight: '600',
    letterSpacing: 0.3,
  },
  textMd: {
    fontSize: 13,
  },
});
