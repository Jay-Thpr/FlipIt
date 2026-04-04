import React, { useState } from 'react';
import {
  View, Text, ScrollView, StyleSheet, Switch, TouchableOpacity,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import {
  Sun, Moon, Smartphone, User, Mail, Camera,
  Bell, BellOff, Activity, Zap, MessageSquare, Tag, Clock,
  ChevronRight, Check, Wifi, WifiOff,
} from 'lucide-react-native';
import { useTheme, ThemePreference } from '../contexts/ThemeContext';

// ─── Types & mock data ────────────────────────────────────────────────────────

interface PlatformEntry {
  id: string;
  name: string;
  shortLabel: string;
  color: string;
  bg: string;
  darkColor: string;
  darkBg: string;
  connected: boolean;
  username?: string;
  apiStatus?: 'valid' | 'expired' | 'missing';
}

const PLATFORMS: PlatformEntry[] = [
  {
    id: 'ebay', name: 'eBay', shortLabel: 'eB',
    color: '#E53935', bg: '#FEE2E2', darkColor: '#FC8181', darkBg: '#3D0F0F',
    connected: true, username: '@reseller_sam', apiStatus: 'valid',
  },
  {
    id: 'depop', name: 'Depop', shortLabel: 'Dp',
    color: '#D1156B', bg: '#FCE7F3', darkColor: '#F472B6', darkBg: '#3D0A24',
    connected: true, username: '@sam.flips', apiStatus: 'valid',
  },
  {
    id: 'mercari', name: 'Mercari', shortLabel: 'Mc',
    color: '#1E40AF', bg: '#DBEAFE', darkColor: '#60A5FA', darkBg: '#0F1E3D',
    connected: false,
  },
  {
    id: 'offerup', name: 'OfferUp', shortLabel: 'Ou',
    color: '#D97706', bg: '#FEF3C7', darkColor: '#FBBF24', darkBg: '#3D2000',
    connected: false,
  },
  {
    id: 'facebook', name: 'Facebook Marketplace', shortLabel: 'Fb',
    color: '#1877F2', bg: '#EFF6FF', darkColor: '#60A5FA', darkBg: '#0F1E3D',
    connected: true, username: '@sam.s', apiStatus: 'expired',
  },
];

const USAGE_STATS = [
  { label: 'Active Listings', value: '5' },
  { label: 'Messages This Month', value: '143' },
  { label: 'Deals Closed', value: '12' },
  { label: 'API Usage', value: '2,841' },
];

// ─── Screen ───────────────────────────────────────────────────────────────────

export default function SettingsScreen() {
  const { colors, theme, setTheme, isDark } = useTheme();
  const [autoReply, setAutoReply] = useState(true);
  const [responseDelay, setResponseDelay] = useState('5 min');
  const [negotiationStyle, setNegotiationStyle] = useState<'aggressive' | 'moderate' | 'passive'>('moderate');
  const [platforms, setPlatforms] = useState<PlatformEntry[]>(PLATFORMS);
  const [notifs, setNotifs] = useState({
    newMessage: true,
    priceDrop: true,
    dealClosed: true,
    listingExpired: false,
  });

  const toggleNotif = (key: keyof typeof notifs) =>
    setNotifs(prev => ({ ...prev, [key]: !prev[key] }));

  const togglePlatform = (id: string) =>
    setPlatforms(prev =>
      prev.map(p => (p.id === id ? { ...p, connected: !p.connected } : p))
    );

  const activeConnected = isDark
    ? { bg: '#052E16', text: '#4ADE80', border: '#14532D' }
    : { bg: '#DCFCE7', text: '#15803D', border: '#BBF7D0' };

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]} edges={['bottom']}>
      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
      >

        {/* ── Appearance ─────────────────────────────────────────────────────── */}
        <SectionHeader title="Appearance" />
        <SectionCard>
          <View style={styles.themeRow}>
            {(['light', 'dark', 'system'] as ThemePreference[]).map(t => {
              const isActive = theme === t;
              return (
                <TouchableOpacity
                  key={t}
                  style={[
                    styles.themeOption,
                    {
                      backgroundColor: isActive ? colors.surfaceRaised : colors.muted,
                      borderColor: isActive ? colors.primary : 'transparent',
                    },
                  ]}
                  onPress={() => setTheme(t)}
                >
                  {t === 'light' && (
                    <Sun size={15} color={isActive ? colors.primary : colors.textMuted} />
                  )}
                  {t === 'dark' && (
                    <Moon size={15} color={isActive ? colors.primary : colors.textMuted} />
                  )}
                  {t === 'system' && (
                    <Smartphone size={15} color={isActive ? colors.primary : colors.textMuted} />
                  )}
                  <Text
                    style={[
                      styles.themeLabel,
                      { color: isActive ? colors.primary : colors.textMuted },
                      isActive && styles.themeLabelActive,
                    ]}
                  >
                    {t.charAt(0).toUpperCase() + t.slice(1)}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </View>
        </SectionCard>

        {/* ── Account ────────────────────────────────────────────────────────── */}
        <SectionHeader title="Account" />
        <SectionCard>
          <SettingRow
            icon={<User size={15} color={colors.primary} />}
            label="Display Name"
            value="Sam S."
            onPress={() => {}}
          />
          <Divider />
          <SettingRow
            icon={<Mail size={15} color={colors.primary} />}
            label="Email"
            value="sam@example.com"
            onPress={() => {}}
          />
          <Divider />
          <SettingRow
            icon={<Camera size={15} color={colors.primary} />}
            label="Profile Photo"
            value="Edit"
            onPress={() => {}}
          />
        </SectionCard>

        {/* ── Platforms ──────────────────────────────────────────────────────── */}
        <SectionHeader title="Connected Platforms" />
        <SectionCard>
          {platforms.map((p, idx) => (
            <React.Fragment key={p.id}>
              {idx > 0 && <Divider />}
              <PlatformRow platform={p} onToggle={() => togglePlatform(p.id)} />
            </React.Fragment>
          ))}
        </SectionCard>

        {/* ── Agent Behavior ─────────────────────────────────────────────────── */}
        <SectionHeader title="Agent Behavior" subtitle="Global defaults — overrideable per item" />
        <SectionCard>
          <SettingToggleRow
            icon={<MessageSquare size={15} color={colors.primary} />}
            label="Auto-Reply"
            value={autoReply}
            onToggle={() => setAutoReply(v => !v)}
          />
          <Divider />
          <SettingRow
            icon={<Clock size={15} color={colors.primary} />}
            label="Response Delay"
            value={responseDelay}
            onPress={() => {}}
          />
          <Divider />
          <View style={styles.settingRow}>
            <View style={styles.settingLeft}>
              <View style={[styles.iconWrap, { backgroundColor: colors.muted }]}>
                <Zap size={15} color={colors.primary} />
              </View>
              <Text style={[styles.settingLabel, { color: colors.textPrimary }]}>
                Negotiation Style
              </Text>
            </View>
            <View style={[styles.segmented, { backgroundColor: colors.muted }]}>
              {(['aggressive', 'moderate', 'passive'] as const).map(s => {
                const isActive = negotiationStyle === s;
                return (
                  <TouchableOpacity
                    key={s}
                    style={[
                      styles.segmentBtn,
                      isActive && [styles.segmentBtnActive, { backgroundColor: colors.surface }],
                    ]}
                    onPress={() => setNegotiationStyle(s)}
                  >
                    <Text
                      style={[
                        styles.segmentText,
                        { color: isActive ? colors.primary : colors.textMuted },
                        isActive && styles.segmentTextActive,
                      ]}
                    >
                      {s.charAt(0).toUpperCase() + s.slice(1)}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </View>
          </View>
        </SectionCard>

        {/* ── Notifications ──────────────────────────────────────────────────── */}
        <SectionHeader title="Notifications" />
        <SectionCard>
          <SettingToggleRow
            icon={<Bell size={15} color={colors.primary} />}
            label="New Message Received"
            value={notifs.newMessage}
            onToggle={() => toggleNotif('newMessage')}
          />
          <Divider />
          <SettingToggleRow
            icon={<Tag size={15} color={colors.primary} />}
            label="Price Drop Detected"
            value={notifs.priceDrop}
            onToggle={() => toggleNotif('priceDrop')}
          />
          <Divider />
          <SettingToggleRow
            icon={<Check size={15} color={colors.primary} />}
            label="Deal Closed"
            value={notifs.dealClosed}
            onToggle={() => toggleNotif('dealClosed')}
          />
          <Divider />
          <SettingToggleRow
            icon={<BellOff size={15} color={colors.primary} />}
            label="Listing Expired"
            value={notifs.listingExpired}
            onToggle={() => toggleNotif('listingExpired')}
          />
        </SectionCard>

        {/* ── Usage ──────────────────────────────────────────────────────────── */}
        <SectionHeader title="Usage" />
        <View style={styles.usageGrid}>
          {USAGE_STATS.map(stat => (
            <View
              key={stat.label}
              style={[
                styles.usageTile,
                { backgroundColor: colors.surface, borderColor: colors.border },
              ]}
            >
              <Text style={[styles.usageValue, { color: colors.primary }]}>{stat.value}</Text>
              <Text style={[styles.usageLabel, { color: colors.textMuted }]}>{stat.label}</Text>
            </View>
          ))}
        </View>

        <View style={{ height: 32 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

// ─── Reusable sub-components ──────────────────────────────────────────────────

function SectionHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  const { colors } = useTheme();
  return (
    <View style={styles.sectionHeader}>
      <Text style={[styles.sectionTitle, { color: colors.textMuted }]}>{title}</Text>
      {subtitle && (
        <Text style={[styles.sectionSubtitle, { color: colors.textMuted }]}>{subtitle}</Text>
      )}
    </View>
  );
}

function SectionCard({ children }: { children: React.ReactNode }) {
  const { colors } = useTheme();
  return (
    <View
      style={[
        styles.card,
        { backgroundColor: colors.surface, borderColor: colors.border },
      ]}
    >
      {children}
    </View>
  );
}

function Divider() {
  const { colors } = useTheme();
  return <View style={[styles.divider, { backgroundColor: colors.border }]} />;
}

function SettingRow({
  icon, label, value, onPress,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  onPress: () => void;
}) {
  const { colors } = useTheme();
  return (
    <TouchableOpacity style={styles.settingRow} onPress={onPress} activeOpacity={0.7}>
      <View style={styles.settingLeft}>
        <View style={[styles.iconWrap, { backgroundColor: colors.muted }]}>{icon}</View>
        <Text style={[styles.settingLabel, { color: colors.textPrimary }]}>{label}</Text>
      </View>
      <View style={styles.settingRight}>
        <Text style={[styles.settingValue, { color: colors.textSecondary }]}>{value}</Text>
        <ChevronRight size={15} color={colors.textMuted} />
      </View>
    </TouchableOpacity>
  );
}

function SettingToggleRow({
  icon, label, value, onToggle,
}: {
  icon: React.ReactNode;
  label: string;
  value: boolean;
  onToggle: () => void;
}) {
  const { colors } = useTheme();
  return (
    <View style={styles.settingRow}>
      <View style={styles.settingLeft}>
        <View style={[styles.iconWrap, { backgroundColor: colors.muted }]}>{icon}</View>
        <Text style={[styles.settingLabel, { color: colors.textPrimary }]}>{label}</Text>
      </View>
      <Switch
        value={value}
        onValueChange={onToggle}
        trackColor={{ true: colors.primary, false: colors.border }}
        thumbColor={colors.white}
      />
    </View>
  );
}

function PlatformRow({
  platform, onToggle,
}: {
  platform: PlatformEntry;
  onToggle: () => void;
}) {
  const { colors, isDark } = useTheme();
  const iconColor = isDark ? platform.darkColor : platform.color;
  const iconBg = isDark ? platform.darkBg : platform.bg;
  const connectedGreen = isDark ? '#4ADE80' : '#15803D';
  const connectedBg = isDark ? '#052E16' : '#DCFCE7';

  return (
    <View style={styles.platformRow}>
      <View style={[styles.platformIcon, { backgroundColor: iconBg }]}>
        <Text style={[styles.platformIconText, { color: iconColor }]}>
          {platform.shortLabel}
        </Text>
      </View>
      <View style={styles.platformInfo}>
        <Text style={[styles.platformName, { color: colors.textPrimary }]}>{platform.name}</Text>
        {platform.connected && platform.username ? (
          <View style={styles.platformMeta}>
            <Text style={[styles.platformUsername, { color: colors.textMuted }]}>
              {platform.username}
            </Text>
            {platform.apiStatus && (
              <View
                style={[
                  styles.apiDot,
                  {
                    backgroundColor:
                      platform.apiStatus === 'valid' ? colors.accent : colors.destructive,
                  },
                ]}
              />
            )}
          </View>
        ) : (
          <Text style={[styles.platformNotConnected, { color: colors.textMuted }]}>
            Not connected
          </Text>
        )}
      </View>
      <View style={styles.platformRight}>
        {platform.connected ? (
          <View style={[styles.connectedBadge, { backgroundColor: connectedBg }]}>
            <Wifi size={10} color={connectedGreen} />
            <Text style={[styles.connectedText, { color: connectedGreen }]}>Connected</Text>
          </View>
        ) : (
          <View
            style={[
              styles.disconnectedBadge,
              { backgroundColor: colors.muted, borderColor: colors.border },
            ]}
          >
            <WifiOff size={10} color={colors.textMuted} />
            <Text style={[styles.disconnectedText, { color: colors.textMuted }]}>Connect</Text>
          </View>
        )}
      </View>
    </View>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1 },
  scrollContent: { paddingHorizontal: 16, paddingTop: 8 },

  sectionHeader: { marginTop: 24, marginBottom: 8, paddingHorizontal: 4 },
  sectionTitle: {
    fontSize: 11,
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: 0.8,
  },
  sectionSubtitle: { fontSize: 11, marginTop: 2 },

  card: {
    borderRadius: 14,
    borderWidth: 1,
    overflow: 'hidden',
  },
  divider: { height: 1 },

  themeRow: { flexDirection: 'row', padding: 10, gap: 8 },
  themeOption: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 5,
    paddingVertical: 10,
    borderRadius: 10,
    borderWidth: 1.5,
  },
  themeLabel: { fontSize: 12, fontWeight: '500' },
  themeLabelActive: { fontWeight: '700' },

  settingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 14,
    paddingVertical: 13,
  },
  settingLeft: { flexDirection: 'row', alignItems: 'center', gap: 10, flex: 1 },
  settingRight: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  iconWrap: {
    width: 28,
    height: 28,
    borderRadius: 7,
    alignItems: 'center',
    justifyContent: 'center',
  },
  settingLabel: { fontSize: 15, fontWeight: '500' },
  settingValue: { fontSize: 14 },

  segmented: {
    flexDirection: 'row',
    borderRadius: 8,
    padding: 2,
    gap: 2,
  },
  segmentBtn: {
    paddingHorizontal: 8,
    paddingVertical: 5,
    borderRadius: 6,
  },
  segmentBtnActive: {},
  segmentText: { fontSize: 11, fontWeight: '500' },
  segmentTextActive: { fontWeight: '700' },

  platformRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 14,
    paddingVertical: 12,
    gap: 10,
  },
  platformIcon: {
    width: 36,
    height: 36,
    borderRadius: 9,
    alignItems: 'center',
    justifyContent: 'center',
  },
  platformIconText: { fontSize: 11, fontWeight: '800' },
  platformInfo: { flex: 1, gap: 2 },
  platformName: { fontSize: 15, fontWeight: '600' },
  platformMeta: { flexDirection: 'row', alignItems: 'center', gap: 5 },
  platformUsername: { fontSize: 12 },
  apiDot: { width: 6, height: 6, borderRadius: 3 },
  platformNotConnected: { fontSize: 12 },
  platformRight: {},
  connectedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    borderRadius: 20,
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  connectedText: { fontSize: 11, fontWeight: '600' },
  disconnectedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    borderRadius: 20,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderWidth: 1,
  },
  disconnectedText: { fontSize: 11, fontWeight: '600' },

  usageGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
  },
  usageTile: {
    width: '47.5%',
    borderRadius: 14,
    borderWidth: 1,
    padding: 16,
    gap: 4,
  },
  usageValue: {
    fontSize: 28,
    fontWeight: '800',
    letterSpacing: -0.5,
  },
  usageLabel: {
    fontSize: 12,
    fontWeight: '500',
  },
});
