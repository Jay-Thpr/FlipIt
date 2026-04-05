import React, { useEffect, useState } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity, ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, router } from 'expo-router';
import { ArrowLeft } from 'lucide-react-native';
import { useTheme } from '../../contexts/ThemeContext';
import { supabase } from '../../lib/supabase';
import { DbCompletedTrade } from '../../lib/types';

function formatFullDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

function formatDuration(startStr: string | null, endStr: string): string {
  if (!startStr) return '--';
  const start = new Date(startStr).getTime();
  const end = new Date(endStr).getTime();
  const diffMs = end - start;
  if (diffMs < 0) return '--';

  const seconds = diffMs / 1000;
  const minutes = seconds / 60;
  const hours = minutes / 60;
  const days = hours / 24;

  // Use the largest unit where the value is >= 1
  if (days >= 1) return `${days.toFixed(2)} days`;
  if (hours >= 1) return `${hours.toFixed(2)} hours`;
  if (minutes >= 1) return `${minutes.toFixed(2)} minutes`;
  return `${seconds.toFixed(2)} seconds`;
}

export default function TradeDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { colors } = useTheme();
  const [trade, setTrade] = useState<DbCompletedTrade | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    loadTrade();
  }, [id]);

  async function loadTrade() {
    const { data } = await supabase
      .from('completed_trades')
      .select('*')
      .eq('id', id)
      .single();
    if (data) setTrade(data as DbCompletedTrade);
    setLoading(false);
  }

  if (loading) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]}>
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
          <ActivityIndicator size="large" color={colors.accent} />
        </View>
      </SafeAreaView>
    );
  }

  if (!trade) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]}>
        <Text style={{ padding: 24, color: colors.textMuted }}>Trade not found.</Text>
      </SafeAreaView>
    );
  }

  const profit = trade.initial_price != null
    ? trade.type === 'Sold'
      ? trade.price - trade.initial_price
      : trade.initial_price - trade.price
    : null;

  const roi = profit != null && trade.initial_price
    ? ((profit / trade.initial_price) * 100).toFixed(1)
    : null;

  const profitColor = profit != null
    ? profit > 0 ? colors.accent : profit < 0 ? colors.destructive : colors.textMuted
    : colors.textMuted;

  const timeToSell = formatDuration(trade.listed_at, trade.completed_at);

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.surface }]} edges={['top']}>
      {/* Header */}
      <View style={[styles.header, { backgroundColor: colors.surface }]}>
        <TouchableOpacity
          onPress={() => router.back()}
          style={styles.backBtn}
          hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
        >
          <ArrowLeft size={20} color={colors.textPrimary} />
        </TouchableOpacity>
        <View style={styles.headerCenter}>
          <Text style={[styles.headerTitle, { color: colors.textPrimary }]} numberOfLines={1}>
            {trade.name}
          </Text>
          <Text style={[styles.headerSubtitle, { color: colors.textMuted }]}>{trade.type}</Text>
        </View>
      </View>

      <ScrollView
        style={{ backgroundColor: colors.background }}
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
      >
        {/* Hero price */}
        <View style={[styles.heroCard, { backgroundColor: colors.surface }]}>
          <Text style={[styles.heroLabel, { color: colors.textMuted }]}>
            {trade.type === 'Sold' ? 'Sold For' : 'Bought For'}
          </Text>
          <Text style={[styles.heroPrice, { color: colors.textPrimary }]}>
            ${trade.price}
          </Text>
          {profit != null && (
            <View style={styles.profitRow}>
              <Text style={[styles.profitValue, { color: profitColor }]}>
                ${Math.abs(profit)}
              </Text>
              {roi != null && (
                <Text style={[styles.roiValue, { color: profitColor }]}>
                  {parseFloat(roi) >= 0 ? '' : '-'}{Math.abs(parseFloat(roi))}% ROI
                </Text>
              )}
            </View>
          )}
        </View>

        {/* Details */}
        <View style={styles.sectionHeader}>
          <Text style={[styles.sectionTitle, { color: colors.textMuted }]}>DETAILS</Text>
        </View>
        <View style={[styles.card, { backgroundColor: colors.surface }]}>
          <DetailRow label="Type" value={trade.type} colors={colors} />
          <View style={[styles.divider, { backgroundColor: colors.divider }]} />
          <DetailRow label="Platform" value={trade.platform} colors={colors} />
          <View style={[styles.divider, { backgroundColor: colors.divider }]} />
          <DetailRow label="Final Price" value={`$${trade.price}`} colors={colors} />
          {trade.initial_price != null && (
            <>
              <View style={[styles.divider, { backgroundColor: colors.divider }]} />
              <DetailRow label="Initial Price" value={`$${trade.initial_price}`} colors={colors} />
            </>
          )}
          {profit != null && (
            <>
              <View style={[styles.divider, { backgroundColor: colors.divider }]} />
              <DetailRow label="Profit" value={`$${Math.abs(profit)}`} colors={colors} valueColor={profitColor} />
            </>
          )}
          {roi != null && (
            <>
              <View style={[styles.divider, { backgroundColor: colors.divider }]} />
              <DetailRow label="ROI" value={`${Math.abs(parseFloat(roi))}%`} colors={colors} valueColor={profitColor} />
            </>
          )}
        </View>

        {/* Timeline */}
        <View style={styles.sectionHeader}>
          <Text style={[styles.sectionTitle, { color: colors.textMuted }]}>TIMELINE</Text>
        </View>
        <View style={[styles.card, { backgroundColor: colors.surface }]}>
          {trade.listed_at && (
            <>
              <DetailRow label="Listed" value={formatFullDate(trade.listed_at)} colors={colors} />
              <View style={[styles.divider, { backgroundColor: colors.divider }]} />
            </>
          )}
          <DetailRow label="Completed" value={formatFullDate(trade.completed_at)} colors={colors} />
          {trade.listed_at && (
            <>
              <View style={[styles.divider, { backgroundColor: colors.divider }]} />
              <DetailRow label="Time to Sell" value={timeToSell} colors={colors} />
            </>
          )}
        </View>

        <View style={{ height: 32 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

function DetailRow({ label, value, colors, valueColor }: {
  label: string; value: string; colors: any; valueColor?: string;
}) {
  return (
    <View style={styles.detailRow}>
      <Text style={[styles.detailLabel, { color: colors.textMuted }]}>{label}</Text>
      <Text style={[styles.detailValue, { color: valueColor ?? colors.textPrimary }]}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    gap: 10,
  },
  backBtn: { width: 36, height: 36, alignItems: 'center', justifyContent: 'center' },
  headerCenter: { flex: 1, gap: 1 },
  headerTitle: { fontSize: 16, fontWeight: '700', letterSpacing: -0.2 },
  headerSubtitle: { fontSize: 12, fontWeight: '500' },
  scrollContent: { paddingHorizontal: 16, paddingTop: 16 },

  // Hero
  heroCard: {
    borderRadius: 12,
    padding: 20,
    alignItems: 'center',
    gap: 6,
  },
  heroLabel: { fontSize: 11, fontWeight: '600', letterSpacing: 0.6, textTransform: 'uppercase' },
  heroPrice: { fontSize: 36, fontWeight: '800', letterSpacing: -0.5, fontVariant: ['tabular-nums'] },
  profitRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginTop: 4 },
  profitValue: { fontSize: 18, fontWeight: '700', fontVariant: ['tabular-nums'] },
  roiValue: { fontSize: 14, fontWeight: '600', fontVariant: ['tabular-nums'] },

  // Sections
  sectionHeader: { marginTop: 24, marginBottom: 8, paddingHorizontal: 4 },
  sectionTitle: { fontSize: 11, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.8 },
  card: { borderRadius: 12, overflow: 'hidden' },
  divider: { height: 1 },

  // Detail rows
  detailRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 14,
    paddingVertical: 13,
  },
  detailLabel: { fontSize: 14, fontWeight: '500' },
  detailValue: { fontSize: 14, fontWeight: '600', fontVariant: ['tabular-nums'] },
});
