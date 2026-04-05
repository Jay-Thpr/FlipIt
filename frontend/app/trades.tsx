import React, { useEffect, useState } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity, ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { ArrowLeft } from 'lucide-react-native';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import { supabase } from '../lib/supabase';

export interface Trade {
  id: string;
  name: string;
  type: 'Sold' | 'Bought';
  platform: string;
  price: number;
  initialPrice?: number | null;
  date: string;
}

export function getTradeProfit(trade: Trade): number | null {
  if (trade.initialPrice == null) return null;
  if (trade.type === 'Sold') return trade.price - trade.initialPrice;
  return trade.initialPrice - trade.price;
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

export default function TradesScreen() {
  const { colors } = useTheme();
  const { user } = useAuth();
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTrades();
  }, []);

  async function loadTrades() {
    const { mockTrades } = require('../data/mockData');
    
    setTrades(
      mockTrades.map((t: any) => ({
        id: t.id,
        name: t.itemName,
        type: 'Sold', // Mocking all as sold for visual profit
        platform: t.platform,
        price: t.sellPrice,
        initialPrice: t.buyPrice,
        date: formatDate(t.date),
      }))
    );
    setLoading(false);
  }

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.surface }]} edges={['top']}>
      <View style={[styles.header, { backgroundColor: colors.surface }]}>
        <TouchableOpacity
          onPress={() => router.back()}
          style={styles.backBtn}
          hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
        >
          <ArrowLeft size={20} color={colors.textPrimary} />
        </TouchableOpacity>
        <Text style={[styles.headerTitle, { color: colors.textPrimary }]}>Trades</Text>
        <View style={{ width: 36 }} />
      </View>

      <ScrollView
        style={{ backgroundColor: colors.background }}
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
      >
        {loading ? (
          <View style={styles.loadingContainer}>
            <ActivityIndicator color={colors.textMuted} />
          </View>
        ) : trades.length === 0 ? (
          <View style={styles.loadingContainer}>
            <Text style={[styles.emptyText, { color: colors.textMuted }]}>No trades yet.</Text>
          </View>
        ) : (
          <View style={[styles.card, { backgroundColor: colors.surface }]}>
            {trades.map((trade, idx) => {
              const profit = getTradeProfit(trade);
              return (
                <React.Fragment key={trade.id}>
                  {idx > 0 && <View style={[styles.divider, { backgroundColor: colors.divider }]} />}
                  <TouchableOpacity
                    style={styles.tradeRow}
                    onPress={() => router.push(`/trade/${trade.id}`)}
                    activeOpacity={0.7}
                  >
                    <View style={styles.tradeInfo}>
                      <Text style={[styles.tradeName, { color: colors.textPrimary }]} numberOfLines={1}>
                        {trade.name}
                      </Text>
                      <Text style={[styles.tradeMeta, { color: colors.textMuted }]}>
                        {trade.type} · {trade.platform} · {trade.date}
                      </Text>
                    </View>
                    <View style={styles.tradeRight}>
                      <Text style={[styles.tradePrice, { color: colors.textPrimary }]}>${trade.price}</Text>
                      {profit != null && (
                        <Text style={[styles.tradeProfit, { color: profit > 0 ? colors.accent : profit < 0 ? colors.destructive : colors.textMuted }]}>
                          ${Math.abs(profit)}
                        </Text>
                      )}
                    </View>
                  </TouchableOpacity>
                </React.Fragment>
              );
            })}
          </View>
        )}
        <View style={{ height: 32 }} />
      </ScrollView>
    </SafeAreaView>
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
  scrollContent: {
    paddingHorizontal: 16,
    paddingTop: 16,
  },
  card: {
    borderRadius: 12,
    overflow: 'hidden',
  },
  divider: { height: 1 },
  tradeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 14,
    paddingVertical: 13,
    gap: 12,
  },
  tradeInfo: {
    flex: 1,
    gap: 2,
  },
  tradeName: {
    fontSize: 14,
    fontWeight: '600',
  },
  tradeMeta: {
    fontSize: 12,
  },
  tradeRight: {
    alignItems: 'flex-end',
    gap: 2,
  },
  tradePrice: {
    fontSize: 15,
    fontWeight: '700',
    fontVariant: ['tabular-nums'],
  },
  tradeProfit: {
    fontSize: 12,
    fontWeight: '600',
    fontVariant: ['tabular-nums'],
  },
  loadingContainer: {
    paddingVertical: 40,
    alignItems: 'center',
  },
  emptyText: {
    fontSize: 14,
  },
});
