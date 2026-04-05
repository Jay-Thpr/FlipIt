import React from 'react';
import { View, Text, Image, StyleSheet } from 'react-native';
import { useTheme } from '../contexts/ThemeContext';

interface Props {
  size?: number;
}

export default function Logo({ size = 20 }: Props) {
  const { colors } = useTheme();
  const iconSize = size * 1.4;  // image is bigger than the text
  const fontSize = size * 0.75;

  return (
    <View style={styles.container}>
      <Image
        source={require('../assets/logo.png')}
        style={{ width: iconSize, height: iconSize, borderRadius: iconSize * 0.2 }}
        resizeMode="cover"
      />
      <Text style={[styles.wordmark, { color: colors.textPrimary, fontSize }]}>
        FlipIt
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 7,
  },
  wordmark: {
    fontWeight: '700',
    letterSpacing: -0.3,
  },
});
