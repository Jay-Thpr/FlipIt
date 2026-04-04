import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '../contexts/ThemeContext';
import { Platform } from '../data/mockData';

interface Props {
  platform: Platform;
  size?: 'sm' | 'md';
}

const DARK_CONFIG: Record<Platform, { label: string; color: string; bg: string }> = {
  ebay:     { label: 'eB', color: '#FC8181', bg: '#3D0F0F' },
  depop:    { label: 'Dp', color: '#F472B6', bg: '#3D0A24' },
  mercari:  { label: 'Mc', color: '#60A5FA', bg: '#0F1E3D' },
  offerup:  { label: 'Ou', color: '#FBBF24', bg: '#3D2000' },
  facebook: { label: 'Fb', color: '#60A5FA', bg: '#0F1E3D' },
};

const LIGHT_CONFIG: Record<Platform, { label: string; color: string; bg: string }> = {
  ebay:     { label: 'eB', color: '#E53935', bg: '#FEE2E2' },
  depop:    { label: 'Dp', color: '#D1156B', bg: '#FCE7F3' },
  mercari:  { label: 'Mc', color: '#1E40AF', bg: '#DBEAFE' },
  offerup:  { label: 'Ou', color: '#D97706', bg: '#FEF3C7' },
  facebook: { label: 'Fb', color: '#1877F2', bg: '#EFF6FF' },
};

export default function PlatformBadge({ platform, size = 'sm' }: Props) {
  const { isDark } = useTheme();
  const config = isDark ? DARK_CONFIG : LIGHT_CONFIG;
  const cfg = config[platform];
  const dim = size === 'md' ? 28 : 20;
  const fontSize = size === 'md' ? 10 : 8;

  return (
    <View
      style={[
        styles.badge,
        {
          backgroundColor: cfg.bg,
          width: dim,
          height: dim,
          borderRadius: size === 'md' ? 6 : 4,
        },
      ]}
    >
      <Text style={[styles.text, { color: cfg.color, fontSize }]}>{cfg.label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  text: {
    fontWeight: '700',
  },
});
