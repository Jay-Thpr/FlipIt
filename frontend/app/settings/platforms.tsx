import React, { useEffect, useState } from 'react';
import { View, Text, ScrollView, StyleSheet, TouchableOpacity, ActivityIndicator } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { ArrowLeft } from 'lucide-react-native';
import { useTheme } from '../../contexts/ThemeContext';
import { useAuth } from '../../contexts/AuthContext';
import { supabase } from '../../lib/supabase';
import { PlatformConnection } from '../../lib/types';

interface PlatformDisplay {
  id: string;
  name: string;
  shortLabel: string;
  color: string;
  bg: string;
  darkColor: string;
  darkBg: string;
}

const PLATFORM_META: Record<string, PlatformDisplay> = {
  ebay: { id: 'ebay', name: 'eBay', shortLabel: 'eB', color: '#E53935', bg: '#FEE2E2', darkColor: '#FC8181', darkBg: '#3D0F0F' },
  depop: { id: 'depop', name: 'Depop', shortLabel: 'Dp', color: '#D1156B', bg: '#FCE7F3', darkColor: '#F472B6', darkBg: '#3D0A24' },
  mercari: { id: 'mercari', name: 'Mercari', shortLabel: 'Mc', color: '#1E40AF', bg: '#DBEAFE', darkColor: '#60A5FA', darkBg: '#0F1E3D' },
  offerup: { id: 'offerup', name: 'OfferUp', shortLabel: 'Ou', color: '#D97706', bg: '#FEF3C7', darkColor: '#FBBF24', darkBg: '#3D2000' },
  facebook: { id: 'facebook', name: 'Facebook Marketplace', shortLabel: 'Fb', color: '#1877F2', bg: '#EFF6FF', darkColor: '#60A5FA', darkBg: '#0F1E3D' },
};

const PLATFORM_ORDER = ['ebay', 'depop', 'mercari', 'offerup', 'facebook'];

export default function PlatformsScreen() {
  const { colors, isDark } = useTheme();
  const { user } = useAuth();
  const [connections, setConnections] = useState<PlatformConnection[]>([]);
  const [loading, setLoading] = useState(true);
  const connectedGreen = isDark ? '#4ADE80' : '#15803D';
  const connectedBg = isDark ? '#052E16' : '#DCFCE7';

  useEffect(() => {
    if (!user) return;
    loadPlatforms();
  }, [user]);

  async function loadPlatforms() {
    if (!user) return;
    const { data } = await supabase
      .from('platform_connections')
      .select('*')
      .eq('user_id', user.id);
    setConnections(data ?? []);
    setLoading(false);
  }

  async function togglePlatform(platform: string) {
    if (!user) return;
    const existing = connections.find(c => c.platform === platform);
    const newConnected = !existing?.connected;

    if (existing) {
      await supabase
        .from('platform_connections')
        .update({
          connected: newConnected,
          connected_at: newConnected ? new Date().toISOString() : null,
        })
        .eq('id', existing.id);
    } else {
      await supabase
        .from('platform_connections')
        .insert({
          user_id: user.id,
          platform,
          connected: true,
          connected_at: new Date().toISOString(),
        });
    }
    loadPlatforms();
  }

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.surface }]} edges={['top']}>
      <View style={[styles.header, { backgroundColor: colors.surface }]}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
          <ArrowLeft size={20} color={colors.textPrimary} />
        </TouchableOpacity>
        <Text style={[styles.headerTitle, { color: colors.textPrimary }]}>Platforms</Text>
        <View style={{ width: 36 }} />
      </View>
      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scrollContent} style={{ backgroundColor: colors.background }}>
        <View style={styles.sectionHeader}>
          <Text style={[styles.sectionTitle, { color: colors.textMuted }]}>PLATFORMS</Text>
        </View>
        <View style={[styles.card, { backgroundColor: colors.surface }]}>
          {loading ? (
            <View style={{ padding: 24, alignItems: 'center' }}>
              <ActivityIndicator color={colors.textMuted} />
            </View>
          ) : (
            PLATFORM_ORDER.map((pid, idx) => {
              const meta = PLATFORM_META[pid];
              const conn = connections.find(c => c.platform === pid);
              const isConnected = true; // Forced to true per user request
              
              return (
                <React.Fragment key={pid}>
                  {idx > 0 && <View style={[styles.divider, { backgroundColor: colors.divider }]} />}
                  <TouchableOpacity style={styles.platformRow} onPress={() => togglePlatform(pid)} activeOpacity={0.7}>
                    <View style={styles.platformInfo}>
                      <Text style={[styles.platformName, { color: colors.textPrimary }]}>{meta.name}</Text>
                      {isConnected && conn?.username ? (
                        <Text style={[styles.platformSub, { color: colors.textMuted }]}>{conn.username}</Text>
                      ) : (
                        <Text style={[styles.platformSub, { color: colors.textMuted }]}>{isConnected ? 'Active' : 'Not connected'}</Text>
                      )}
                    </View>
                    {isConnected ? (
                      <View style={[styles.badge, { backgroundColor: connectedBg }]}>
                        <Text style={[styles.badgeText, { color: connectedGreen }]}>Connected</Text>
                      </View>
                    ) : (
                      <View style={[styles.badge, { backgroundColor: colors.muted }]}>
                        <Text style={[styles.badgeText, { color: colors.textMuted }]}>Connect</Text>
                      </View>
                    )}
                  </TouchableOpacity>
                </React.Fragment>
              );
            })
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
  platformRow: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 14, paddingVertical: 12, gap: 10 },
  platformIcon: { width: 36, height: 36, borderRadius: 8, alignItems: 'center', justifyContent: 'center' },
  platformIconText: { fontSize: 11, fontWeight: '800' },
  platformInfo: { flex: 1, gap: 2 },
  platformName: { fontSize: 15, fontWeight: '600' },
  platformSub: { fontSize: 12 },
  badge: { borderRadius: 6, paddingHorizontal: 8, paddingVertical: 4 },
  badgeText: { fontSize: 11, fontWeight: '600' },
});
