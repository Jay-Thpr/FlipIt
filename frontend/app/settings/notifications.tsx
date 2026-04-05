import React, { useEffect, useState } from 'react';
import { View, Text, ScrollView, StyleSheet, Switch, TouchableOpacity, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { ArrowLeft, Bell, BellOff, Tag, Check } from 'lucide-react-native';
import { useTheme } from '../../contexts/ThemeContext';
import { useAuth } from '../../contexts/AuthContext';
import { supabase } from '../../lib/supabase';

interface NotifState {
  notif_new_message: boolean;
  notif_price_drop: boolean;
  notif_deal_closed: boolean;
  notif_listing_expired: boolean;
}

export default function NotificationsScreen() {
  const { colors } = useTheme();
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [notifs, setNotifs] = useState<NotifState>({
    notif_new_message: true,
    notif_price_drop: true,
    notif_deal_closed: true,
    notif_listing_expired: false,
  });

  useEffect(() => {
    if (!user) return;
    loadSettings();
  }, [user]);

  async function loadSettings() {
    if (!user) return;
    const { data } = await supabase
      .from('user_settings')
      .select('notif_new_message, notif_price_drop, notif_deal_closed, notif_listing_expired')
      .eq('user_id', user.id)
      .single();
    if (data) {
      setNotifs({
        notif_new_message: data.notif_new_message,
        notif_price_drop: data.notif_price_drop,
        notif_deal_closed: data.notif_deal_closed,
        notif_listing_expired: data.notif_listing_expired,
      });
    }
    setLoading(false);
  }

  async function toggleNotif(key: keyof NotifState) {
    const newVal = !notifs[key];
    setNotifs(prev => ({ ...prev, [key]: newVal }));
    if (user) {
      await supabase.from('user_settings').update({ [key]: newVal }).eq('user_id', user.id);
    }
  }

  const rows: { key: keyof NotifState; label: string; icon: React.ReactNode }[] = [
    { key: 'notif_new_message', label: 'New Message Received', icon: <Bell size={15} color={colors.textSecondary} /> },
    { key: 'notif_price_drop', label: 'Price Drop Detected', icon: <Tag size={15} color={colors.textSecondary} /> },
    { key: 'notif_deal_closed', label: 'Deal Closed', icon: <Check size={15} color={colors.textSecondary} /> },
    { key: 'notif_listing_expired', label: 'Listing Expired', icon: <BellOff size={15} color={colors.textSecondary} /> },
  ];

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.surface }]} edges={['top']}>
      <View style={[styles.header, { backgroundColor: colors.surface }]}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
          <ArrowLeft size={20} color={colors.textPrimary} />
        </TouchableOpacity>
        <Text style={[styles.headerTitle, { color: colors.textPrimary }]}>Notifications</Text>
        <View style={{ width: 36 }} />
      </View>
      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scrollContent} style={{ backgroundColor: colors.background }}>
        <View style={styles.sectionHeader}>
          <Text style={[styles.sectionTitle, { color: colors.textMuted }]}>NOTIFICATIONS</Text>
        </View>
        <View style={[styles.card, { backgroundColor: colors.surface }]}>
          {loading ? (
            <View style={{ padding: 24, alignItems: 'center' }}>
              <ActivityIndicator color={colors.textMuted} />
            </View>
          ) : (
            rows.map((r, idx) => (
              <React.Fragment key={r.key}>
                {idx > 0 && <View style={[styles.divider, { backgroundColor: colors.divider }]} />}
                <View style={styles.row}>
                  <View style={styles.rowLeft}>
                    <View style={[styles.iconWrap, { backgroundColor: colors.muted }]}>{r.icon}</View>
                    <Text style={[styles.rowLabel, { color: colors.textPrimary }]}>{r.label}</Text>
                  </View>
                  <Switch
                    value={notifs[r.key]}
                    onValueChange={() => toggleNotif(r.key)}
                    trackColor={{ true: colors.accent, false: colors.muted }}
                    thumbColor={colors.white}
                  />
                </View>
              </React.Fragment>
            ))
          )}
        </View>
        <View style={{ height: 32 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 12, gap: 10 },
  backBtn: { width: 36, height: 36, alignItems: 'center', justifyContent: 'center' },
  headerTitle: { flex: 1, fontSize: 16, fontWeight: '700', letterSpacing: -0.2 },
  scrollContent: { paddingHorizontal: 16, paddingTop: 8 },
  sectionHeader: { marginTop: 24, marginBottom: 8, paddingHorizontal: 4 },
  sectionTitle: { fontSize: 11, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.8 },
  card: { borderRadius: 12, overflow: 'hidden' },
  divider: { height: 1 },
  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 14, paddingVertical: 13 },
  rowLeft: { flexDirection: 'row', alignItems: 'center', gap: 10, flex: 1 },
  rowLabel: { fontSize: 15, fontWeight: '500' },
  iconWrap: { width: 28, height: 28, borderRadius: 7, alignItems: 'center', justifyContent: 'center' },
});
