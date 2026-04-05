import React, { useEffect, useState } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity, ActivityIndicator,
  TextInput, Alert, Image,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import {
  ArrowLeft, Sun, Moon, Smartphone, User, Mail, Camera, Trash2,
} from 'lucide-react-native';
import { useTheme, ThemePreference } from '../../contexts/ThemeContext';
import { useAuth } from '../../contexts/AuthContext';
import { supabase } from '../../lib/supabase';
import { pickImage } from '../../lib/imagePicker';
import { Profile } from '../../lib/types';

export default function AccountScreen() {
  const { colors, theme, setTheme } = useTheme();
  const { user, signOut } = useAuth();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [editingName, setEditingName] = useState(false);
  const [nameDraft, setNameDraft] = useState('');
  const [stats, setStats] = useState({ items: '0', messages: '0' });

  useEffect(() => {
    if (!user) return;
    loadData();
  }, [user]);

  async function loadData() {
    if (!user) return;
    setLoading(true);

    // Get current month boundaries
    const now = new Date();
    const monthStart = new Date(now.getFullYear(), now.getMonth(), 1).toISOString();
    const monthEnd = new Date(now.getFullYear(), now.getMonth() + 1, 0, 23, 59, 59).toISOString();

    const [profileRes, itemsRes, messagesRes] = await Promise.all([
      supabase.from('profiles').select('*').eq('id', user.id).single(),
      supabase.from('items').select('id', { count: 'exact' }).eq('user_id', user.id),
      supabase
        .from('messages')
        .select('id, conversation_id, conversations!inner(item_id, items!inner(user_id))', { count: 'exact' })
        .eq('conversations.items.user_id', user.id)
        .gte('created_at', monthStart)
        .lte('created_at', monthEnd),
    ]);

    if (profileRes.data) {
      setProfile(profileRes.data);
      setNameDraft(profileRes.data.display_name);
    }
    setStats({
      items: String(itemsRes.count ?? 0),
      messages: String(messagesRes.count ?? 0),
    });
    setLoading(false);
  }

  async function handleThemeChange(t: ThemePreference) {
    setTheme(t);
    if (user) {
      await supabase.from('user_settings').update({ theme_preference: t }).eq('user_id', user.id);
    }
  }

  async function handleSaveName() {
    if (!user || !nameDraft.trim()) return;
    setEditingName(false);
    const trimmed = nameDraft.trim();
    setProfile(prev => prev ? { ...prev, display_name: trimmed } : prev);
    await supabase.from('profiles').update({ display_name: trimmed }).eq('id', user.id);
  }

  async function handleEditProfilePicture() {
    if (!user) return;
    const uris = await pickImage({ shape: 'circle' });
    if (uris.length === 0) return;

    const uri = uris[0];
    const ext = uri.split('.').pop()?.toLowerCase() || 'jpg';
    const fileName = `avatar.${ext}`;
    const path = `${user.id}/${fileName}`;

    const formData = new FormData();
    formData.append('', {
      uri,
      name: fileName,
      type: `image/${ext === 'jpg' ? 'jpeg' : ext}`,
    } as any);

    await supabase.storage.from('item-photos').upload(path, formData, {
      contentType: 'multipart/form-data',
      upsert: true,
    });

    const { data: urlData } = supabase.storage.from('item-photos').getPublicUrl(path);
    const avatarUrl = `${urlData.publicUrl}?t=${Date.now()}`; // cache bust
    await supabase.from('profiles').update({ avatar_url: avatarUrl }).eq('id', user.id);
    setProfile(prev => prev ? { ...prev, avatar_url: avatarUrl } : prev);
  }

  function handleDeleteAccount() {
    Alert.alert(
      'Delete Account',
      'This will permanently delete your account and all your data. This cannot be undone.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete Forever',
          style: 'destructive',
          onPress: async () => {
            // Delete user data (cascades handle related tables)
            if (user) {
              await supabase.from('items').delete().eq('user_id', user.id);
              await supabase.from('completed_trades').delete().eq('user_id', user.id);
              await supabase.from('user_settings').delete().eq('user_id', user.id);
              await supabase.from('platform_connections').delete().eq('user_id', user.id);
              await supabase.from('profiles').delete().eq('id', user.id);
            }
            await signOut();
          },
        },
      ]
    );
  }

  const displayName = profile?.display_name || user?.user_metadata?.display_name || 'User';
  const email = profile?.email || user?.email || '';
  const avatarUrl = profile?.avatar_url;
  const initials = displayName.split(' ').map((w: string) => w[0]).join('').toUpperCase().slice(0, 2);

  const USAGE_STATS = [
    { label: 'Total Items', value: stats.items },
    { label: 'Messages This Month', value: stats.messages },
  ];

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.surface }]} edges={['top']}>
      <View style={[styles.header, { backgroundColor: colors.surface }]}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
          <ArrowLeft size={20} color={colors.textPrimary} />
        </TouchableOpacity>
        <Text style={[styles.headerTitle, { color: colors.textPrimary }]}>Account</Text>
        <View style={{ width: 36 }} />
      </View>
      <ScrollView
        style={{ backgroundColor: colors.background }}
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
      >
        {/* Profile Picture */}
        <View style={styles.avatarSection}>
          <TouchableOpacity onPress={handleEditProfilePicture} activeOpacity={0.7} style={styles.avatarWrap}>
            {avatarUrl ? (
              <Image source={{ uri: avatarUrl }} style={styles.avatarImage} />
            ) : (
              <View style={[styles.avatarFallback, { backgroundColor: colors.primary }]}>
                <Text style={styles.avatarInitials}>{initials}</Text>
              </View>
            )}
            <View style={[styles.cameraBadge, { backgroundColor: colors.surfaceRaised }]}>
              <Camera size={12} color={colors.textPrimary} />
            </View>
          </TouchableOpacity>
          <TouchableOpacity onPress={handleEditProfilePicture}>
            <Text style={[styles.editPhotoText, { color: colors.textSecondary }]}>Edit Profile Picture</Text>
          </TouchableOpacity>
        </View>

        {/* Appearance */}
        <SectionHeader title="Appearance" colors={colors} />
        <View style={[styles.card, { backgroundColor: colors.surface }]}>
          <View style={styles.themeRow}>
            {(['light', 'dark', 'system'] as ThemePreference[]).map(t => {
              const isActive = theme === t;
              return (
                <TouchableOpacity
                  key={t}
                  style={[styles.themeOption, { backgroundColor: isActive ? colors.surfaceRaised : 'transparent' }]}
                  onPress={() => handleThemeChange(t)}
                >
                  {t === 'light' && <Sun size={14} color={isActive ? colors.textPrimary : colors.textMuted} />}
                  {t === 'dark' && <Moon size={14} color={isActive ? colors.textPrimary : colors.textMuted} />}
                  {t === 'system' && <Smartphone size={14} color={isActive ? colors.textPrimary : colors.textMuted} />}
                  <Text style={[styles.themeLabel, { color: isActive ? colors.textPrimary : colors.textMuted }, isActive && styles.themeLabelActive]}>
                    {t.charAt(0).toUpperCase() + t.slice(1)}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </View>
        </View>

        {/* Account */}
        <SectionHeader title="Account" colors={colors} />
        <View style={[styles.card, { backgroundColor: colors.surface }]}>
          {/* Display Name — tappable to edit */}
          <TouchableOpacity
            style={styles.settingRow}
            activeOpacity={0.7}
            onPress={() => { setNameDraft(displayName); setEditingName(true); }}
          >
            <View style={styles.settingLeft}>
              <View style={[styles.iconWrap, { backgroundColor: colors.muted }]}>
                <User size={15} color={colors.textSecondary} />
              </View>
              <Text style={[styles.settingLabel, { color: colors.textPrimary }]}>Display Name</Text>
            </View>
            {editingName ? (
              <TextInput
                style={[styles.nameInput, { color: colors.textPrimary, borderBottomColor: colors.accent }]}
                value={nameDraft}
                onChangeText={setNameDraft}
                onBlur={handleSaveName}
                onSubmitEditing={handleSaveName}
                autoFocus
                returnKeyType="done"
                selectTextOnFocus
              />
            ) : (
              <View style={styles.settingRight}>
                <Text style={[styles.settingValue, { color: colors.textSecondary }]}>{displayName}</Text>
              </View>
            )}
          </TouchableOpacity>

          <View style={[styles.divider, { backgroundColor: colors.divider }]} />

          {/* Email — read only, grayed out */}
          <View style={[styles.settingRow, { opacity: 0.5 }]}>
            <View style={styles.settingLeft}>
              <View style={[styles.iconWrap, { backgroundColor: colors.muted }]}>
                <Mail size={15} color={colors.textSecondary} />
              </View>
              <Text style={[styles.settingLabel, { color: colors.textPrimary }]}>Email</Text>
            </View>
            <View style={styles.settingRight}>
              <Text style={[styles.settingValue, { color: colors.textSecondary }]}>{email}</Text>
            </View>
          </View>
        </View>

        {/* Usage */}
        <SectionHeader title="Usage" colors={colors} />
        <View style={[styles.card, { backgroundColor: colors.surface }]}>
          {loading ? (
            <View style={{ padding: 24, alignItems: 'center' }}>
              <ActivityIndicator color={colors.textMuted} />
            </View>
          ) : (
            <View style={styles.usageGrid}>
              {USAGE_STATS.map(stat => (
                <View key={stat.label} style={[styles.usageTile, { borderRightColor: colors.divider, borderBottomColor: colors.divider }]}>
                  <Text style={[styles.usageValue, { color: colors.textPrimary }]}>{stat.value}</Text>
                  <Text style={[styles.usageLabel, { color: colors.textMuted }]}>{stat.label}</Text>
                </View>
              ))}
            </View>
          )}
        </View>

        {/* Delete Account */}
        <View style={styles.dangerSection}>
          <TouchableOpacity
            style={styles.deleteBtn}
            onPress={handleDeleteAccount}
            activeOpacity={0.7}
          >
            <Trash2 size={15} color={colors.destructive} />
            <Text style={[styles.deleteBtnText, { color: colors.destructive }]}>Delete Account</Text>
          </TouchableOpacity>
        </View>

        <View style={{ height: 32 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

function SectionHeader({ title, colors }: { title: string; colors: any }) {
  return (
    <View style={styles.sectionHeader}>
      <Text style={[styles.sectionTitle, { color: colors.textMuted }]}>{title}</Text>
    </View>
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

  // Avatar
  avatarSection: { alignItems: 'center', marginTop: 16, marginBottom: 8, gap: 10 },
  avatarWrap: { position: 'relative' },
  avatarImage: { width: 80, height: 80, borderRadius: 40 },
  avatarFallback: { width: 80, height: 80, borderRadius: 40, alignItems: 'center', justifyContent: 'center' },
  avatarInitials: { fontSize: 28, fontWeight: '700', color: '#FFFFFF' },
  cameraBadge: { position: 'absolute', bottom: 0, right: 0, width: 28, height: 28, borderRadius: 14, alignItems: 'center', justifyContent: 'center' },
  editPhotoText: { fontSize: 14, fontWeight: '600' },

  // Theme
  themeRow: { flexDirection: 'row', padding: 8, gap: 6 },
  themeOption: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 5, paddingVertical: 10, borderRadius: 8 },
  themeLabel: { fontSize: 12, fontWeight: '500' },
  themeLabelActive: { fontWeight: '700' },

  // Settings rows
  settingRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 14, paddingVertical: 13 },
  settingLeft: { flexDirection: 'row', alignItems: 'center', gap: 10, flex: 1 },
  settingRight: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  iconWrap: { width: 28, height: 28, borderRadius: 7, alignItems: 'center', justifyContent: 'center' },
  settingLabel: { fontSize: 15, fontWeight: '500' },
  settingValue: { fontSize: 14 },
  nameInput: { fontSize: 14, fontWeight: '600', borderBottomWidth: 1, paddingVertical: 2, minWidth: 100, textAlign: 'right' },

  // Usage
  usageGrid: { flexDirection: 'row', flexWrap: 'wrap' },
  usageTile: { width: '50%', padding: 16, gap: 4, borderRightWidth: 1, borderBottomWidth: 1 },
  usageValue: { fontSize: 28, fontWeight: '800', letterSpacing: -0.5, fontVariant: ['tabular-nums'] },
  usageLabel: { fontSize: 12, fontWeight: '500' },

  // Delete
  dangerSection: { marginTop: 40, alignItems: 'center' },
  deleteBtn: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingVertical: 14 },
  deleteBtnText: { fontSize: 14, fontWeight: '500' },
});
