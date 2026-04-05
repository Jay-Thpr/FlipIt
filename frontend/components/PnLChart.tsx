import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Dimensions } from 'react-native';
import Svg, { Path, Defs, LinearGradient, Stop, Line } from 'react-native-svg';
import { useTheme } from '../contexts/ThemeContext';

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const CHART_OUTER_WIDTH = SCREEN_WIDTH - 32;
const LABEL_WIDTH = 36;                          // reserved for y-axis labels on the left
const CHART_WIDTH = CHART_OUTER_WIDTH - LABEL_WIDTH;  // grid lines + curve start after labels
const CHART_HEIGHT = 140;
const CHART_PADDING_TOP = 10;
const CHART_PADDING_BOTTOM = 14;

export interface PnLDataPoint {
  date: string;      // Display label (e.g. "Apr 4")
  isoDate?: string;  // Raw ISO date for filtering
  value: number;
}

interface Props {
  data: PnLDataPoint[];
}

const PERIODS = ['1W', '1M', '3M', 'ALL'] as const;

function buildPath(values: number[], width: number, height: number, offsetX: number = 0): { line: string; area: string } {
  if (values.length < 2) return { line: 'M0,0', area: 'M0,0' };

  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const usableHeight = height - CHART_PADDING_TOP - CHART_PADDING_BOTTOM;

  const points = values.map((v, i) => ({
    x: offsetX + (i / (values.length - 1)) * width,
    y: CHART_PADDING_TOP + usableHeight - ((v - min) / range) * usableHeight,
  }));

  let line = `M${points[0].x},${points[0].y}`;
  for (let i = 1; i < points.length; i++) {
    const prev = points[i - 1];
    const curr = points[i];
    const cpx = (prev.x + curr.x) / 2;
    line += ` C${cpx},${prev.y} ${cpx},${curr.y} ${curr.x},${curr.y}`;
  }

  const area = `${line} L${points[points.length - 1].x},${height} L${points[0].x},${height} Z`;
  return { line, area };
}

export default function PnLChart({ data }: Props) {
  const { colors, isDark } = useTheme();
  const [period, setPeriod] = useState<typeof PERIODS[number]>('ALL');

  // Filter by period
  const now = new Date();
  const periodDays: Record<string, number> = { '1W': 7, '1M': 30, '3M': 90, ALL: 9999 };
  const cutoff = new Date(now.getTime() - periodDays[period] * 86400000);

  const filtered = data.filter(d => {
    if (d.isoDate) return new Date(d.isoDate) >= cutoff;
    // Fallback: try parsing display date
    const date = new Date(d.date);
    return !isNaN(date.getTime()) && date >= cutoff;
  });

  // Compute cumulative P&L
  const cumulative = filtered.reduce<number[]>((acc, d) => {
    const prev = acc.length > 0 ? acc[acc.length - 1] : 0;
    acc.push(prev + d.value);
    return acc;
  }, []);

  // Always start from 0
  const values = [0, ...cumulative];
  const currentValue = values[values.length - 1];
  // Color: green if positive, red if negative, neutral if zero
  const valueColor = currentValue > 0 ? colors.accent : currentValue < 0 ? colors.destructive : colors.textMuted;
  // For chart line: always green when zero or positive, red when negative
  const lineColor = currentValue >= 0 ? colors.accent : colors.destructive;

  // No data at all OR no trades in this period — show flat green line at $0
  const showFlatLine = data.length === 0 || filtered.length === 0;

  // Render: flat green line if no trades in period, otherwise full chart
  if (showFlatLine) {
    const topY = CHART_PADDING_TOP;
    const midY = CHART_HEIGHT / 2;
    const botY = CHART_HEIGHT - CHART_PADDING_BOTTOM;
    return (
      <View style={styles.container}>
        <View style={styles.valueRow}>
          <Text style={[styles.valueLabel, { color: colors.textMuted }]}>Net Profit</Text>
          <Text style={[styles.value, { color: colors.textMuted }]}>$0</Text>
        </View>
        <View style={styles.chartWrap}>
          <Svg width={CHART_OUTER_WIDTH} height={CHART_HEIGHT}>
            {/* 3 grid lines — start after label area */}
            <Line x1={LABEL_WIDTH} y1={topY} x2={CHART_OUTER_WIDTH} y2={topY} stroke={colors.divider} strokeWidth={1} />
            <Line x1={LABEL_WIDTH} y1={midY} x2={CHART_OUTER_WIDTH} y2={midY} stroke={colors.divider} strokeWidth={1} />
            <Line x1={LABEL_WIDTH} y1={botY} x2={CHART_OUTER_WIDTH} y2={botY} stroke={colors.divider} strokeWidth={1} />
            {/* Flat green curve at center */}
            <Line x1={LABEL_WIDTH} y1={midY} x2={CHART_OUTER_WIDTH} y2={midY} stroke={colors.accent} strokeWidth={1.5} strokeOpacity={0.5} />
          </Svg>
          {/* Labels on the left — show a reasonable default range */}
          <View style={[styles.yLabel, { top: topY - 6 }]}>
            <Text style={[styles.yLabelText, { color: colors.textMuted }]}>$50</Text>
          </View>
          <View style={[styles.yLabel, { top: midY - 6 }]}>
            <Text style={[styles.yLabelText, { color: colors.textMuted }]}>$0</Text>
          </View>
          <View style={[styles.yLabel, { top: botY - 6 }]}>
            <Text style={[styles.yLabelText, { color: colors.textMuted }]}>-$50</Text>
          </View>
        </View>
        <View style={[styles.periodRow, { backgroundColor: colors.surface }]}>
          {PERIODS.map(p => {
            const active = period === p;
            return (
              <TouchableOpacity
                key={p}
                style={[styles.periodTab, active && { backgroundColor: colors.surfaceRaised }]}
                onPress={() => setPeriod(p)}
              >
                <Text style={[
                  styles.periodText,
                  { color: active ? colors.textPrimary : colors.textMuted },
                  active && styles.periodTextActive,
                ]}>
                  {p}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>
      </View>
    );
  }

  const { line, area } = buildPath(values, CHART_WIDTH, CHART_HEIGHT, LABEL_WIDTH);

  let min = Math.min(...values);
  let max = Math.max(...values);
  // Ensure a minimum visible spread on the y-axis
  if (max - min < 20) {
    const center = Math.round((min + max) / 2);
    min = center - 10;
    max = center + 10;
  }
  const mid = Math.round((min + max) / 2);
  const range = max - min || 1;
  const usableHeight = CHART_HEIGHT - CHART_PADDING_TOP - CHART_PADDING_BOTTOM;
  const yForValue = (v: number) =>
    CHART_PADDING_TOP + usableHeight - ((v - min) / range) * usableHeight;

  return (
    <View style={styles.container}>
      {/* Hero P&L value — color only, no +/- */}
      <View style={styles.valueRow}>
        <Text style={[styles.valueLabel, { color: colors.textMuted }]}>Net Profit</Text>
        <Text style={[styles.value, { color: valueColor }]}>
          ${Math.abs(currentValue)}
        </Text>
      </View>

      {/* Chart */}
      <View style={styles.chartWrap}>
        <Svg width={CHART_OUTER_WIDTH} height={CHART_HEIGHT}>
          <Defs>
            <LinearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
              <Stop offset="0" stopColor={lineColor} stopOpacity={isDark ? 0.2 : 0.12} />
              <Stop offset="1" stopColor={lineColor} stopOpacity={0} />
            </LinearGradient>
          </Defs>
          {/* Grid lines start after label area */}
          <Line x1={LABEL_WIDTH} y1={yForValue(max)} x2={CHART_OUTER_WIDTH} y2={yForValue(max)} stroke={colors.divider} strokeWidth={1} />
          <Line x1={LABEL_WIDTH} y1={yForValue(mid)} x2={CHART_OUTER_WIDTH} y2={yForValue(mid)} stroke={colors.divider} strokeWidth={1} />
          <Line x1={LABEL_WIDTH} y1={yForValue(min)} x2={CHART_OUTER_WIDTH} y2={yForValue(min)} stroke={colors.divider} strokeWidth={1} />
          <Path d={area} fill="url(#areaGrad)" />
          <Path d={line} fill="none" stroke={lineColor} strokeWidth={1.5} />
        </Svg>
        {/* Labels positioned to the right of grid lines */}
        <View style={[styles.yLabel, { top: yForValue(max) - 6 }]}>
          <Text style={[styles.yLabelText, { color: colors.textMuted }]}>${max}</Text>
        </View>
        <View style={[styles.yLabel, { top: yForValue(mid) - 6 }]}>
          <Text style={[styles.yLabelText, { color: colors.textMuted }]}>${mid}</Text>
        </View>
        <View style={[styles.yLabel, { top: yForValue(min) - 6 }]}>
          <Text style={[styles.yLabelText, { color: colors.textMuted }]}>${min}</Text>
        </View>
      </View>

      {/* Period tabs */}
      <View style={[styles.periodRow, { backgroundColor: colors.surface }]}>
        {PERIODS.map(p => {
          const active = period === p;
          return (
            <TouchableOpacity
              key={p}
              style={[styles.periodTab, active && { backgroundColor: colors.surfaceRaised }]}
              onPress={() => setPeriod(p)}
            >
              <Text style={[
                styles.periodText,
                { color: active ? colors.textPrimary : colors.textMuted },
                active && styles.periodTextActive,
              ]}>
                {p}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: 8,
  },
  emptyContainer: {
    paddingVertical: 32,
    alignItems: 'center',
  },
  emptyText: {
    fontSize: 13,
    fontWeight: '500',
    textAlign: 'center',
  },
  emptyOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 4,
  },
  emptyTitle: {
    fontSize: 16,
    fontWeight: '700',
  },
  emptyHint: {
    fontSize: 12,
    fontWeight: '500',
    textAlign: 'center',
    paddingHorizontal: 24,
  },
  valueRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    paddingHorizontal: 4,
  },
  valueLabel: {
    fontSize: 11,
    fontWeight: '600',
    letterSpacing: 0.6,
    textTransform: 'uppercase',
  },
  value: {
    fontSize: 24,
    fontWeight: '800',
    letterSpacing: -0.5,
    fontVariant: ['tabular-nums'],
  },
  chartWrap: {
    position: 'relative',
    height: CHART_HEIGHT,
  },
  yLabel: {
    position: 'absolute',
    left: 0,
  },
  yLabelText: {
    fontSize: 9,
    fontWeight: '500',
    fontVariant: ['tabular-nums'],
  },
  periodRow: {
    flexDirection: 'row',
    borderRadius: 8,
    padding: 2,
    gap: 2,
  },
  periodTab: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: 6,
    borderRadius: 6,
  },
  periodText: {
    fontSize: 12,
    fontWeight: '500',
  },
  periodTextActive: {
    fontWeight: '700',
  },
});
