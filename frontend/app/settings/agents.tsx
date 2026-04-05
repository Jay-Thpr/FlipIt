import React, { useEffect, useState } from 'react';
import {
  View, Text, ScrollView, StyleSheet, Switch, TouchableOpacity, ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import { ArrowLeft, MessageSquare, Clock, Zap, Mic } from 'lucide-react-native';
import { useTheme } from '../../contexts/ThemeContext';
import { useAuth } from '../../contexts/AuthContext';
import { supabase } from '../../lib/supabase';
import { NegotiationStyle, ReplyTone } from '../../lib/types';
import { getAgents, getHealth, AgentInfo } from '../../lib/api';

export default function AgentsScreen() {
  const { colors } = useTheme();
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [autoReply, setAutoReply] = useState(true);
  const [responseDelay, setResponseDelay] = useState('5 min');
  const [negotiationStyle, setNegotiationStyle] = useState<NegotiationStyle>('moderate');
  const [replyTone, setReplyTone] = useState<ReplyTone>('professional');
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [backendStatus, setBackendStatus] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    loadSettings();
  }, [user]);

  useEffect(() => {
    getHealth()
      .then(h => setBackendStatus(h.status))
      .catch(() => setBackendStatus('offline'));
    getAgents()
      .then(data => setAgents(data.agents))
      .catch(() => {});
  }, []);

  async function loadSettings() {
    if (!user) return;
    const { data } = await supabase
      .from('user_settings')
      .select('*')
      .eq('user_id', user.id)
      .single();
    if (data) {
      setAutoReply(data.auto_reply);
      setResponseDelay(data.response_delay);
      setNegotiationStyle(data.negotiation_style);
      setReplyTone(data.reply_tone);
    }
    setLoading(false);
  }

  async function updateSetting(updates: Record<string, any>) {
    if (!user) return;
    await supabase.from('user_settings').update(updates).eq('user_id', user.id);
  }

  function handleAutoReplyToggle() {
    const newVal = !autoReply;
    setAutoReply(newVal);
    updateSetting({ auto_reply: newVal });
  }

  function handleNegotiationChange(s: NegotiationStyle) {
    setNegotiationStyle(s);
    updateSetting({ negotiation_style: s });
  }

  function handleToneChange(t: ReplyTone) {
    setReplyTone(t);
    updateSetting({ reply_tone: t });
  }

  if (loading) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: colors.surface }]} edges={['top']}>
        <View style={[styles.header, { backgroundColor: colors.surface }]}>
          <TouchableOpacity onPress={() => router.back()} style={styles.backBtn} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
            <ArrowLeft size={20} color={colors.textPrimary} />
          </TouchableOpacity>
          <Text style={[styles.headerTitle, { color: colors.textPrimary }]}>Agent Behaviors</Text>
          <View style={{ width: 36 }} />
        </View>
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: colors.background }}>
          <ActivityIndicator color={colors.textMuted} />
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.surface }]} edges={['top']}>
      <View style={[styles.header, { backgroundColor: colors.surface }]}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backBtn} hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}>
          <ArrowLeft size={20} color={colors.textPrimary} />
        </TouchableOpacity>
        <Text style={[styles.headerTitle, { color: colors.textPrimary }]}>Agent Behaviors</Text>
        <View style={{ width: 36 }} />
      </View>
      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scrollContent} style={{ backgroundColor: colors.background }}>
        <View style={styles.sectionHeader}>
          <Text style={[styles.sectionTitle, { color: colors.textMuted }]}>DEFAULT AGENT BEHAVIOR</Text>
        </View>
        <View style={[styles.card, { backgroundColor: colors.surface }]}>
          {/* Auto-Reply */}
          <View style={styles.row}>
            <View style={styles.rowLeft}>
              <View style={[styles.iconWrap, { backgroundColor: colors.muted }]}>
                <MessageSquare size={15} color={colors.textSecondary} />
              </View>
              <Text style={[styles.rowLabel, { color: colors.textPrimary }]}>Auto-Reply</Text>
            </View>
            <Switch
              value={autoReply}
              onValueChange={handleAutoReplyToggle}
              trackColor={{ true: colors.accent, false: colors.muted }}
              thumbColor={colors.white}
            />
          </View>

          <View style={[styles.divider, { backgroundColor: colors.divider }]} />

          {/* Response Delay */}
          <TouchableOpacity style={styles.row} activeOpacity={0.7}>
            <View style={styles.rowLeft}>
              <View style={[styles.iconWrap, { backgroundColor: colors.muted }]}>
                <Clock size={15} color={colors.textSecondary} />
              </View>
              <Text style={[styles.rowLabel, { color: colors.textPrimary }]}>Response Delay</Text>
            </View>
            <Text style={[styles.rowValue, { color: colors.textSecondary }]}>{responseDelay}</Text>
          </TouchableOpacity>

          <View style={[styles.divider, { backgroundColor: colors.divider }]} />

          {/* Negotiation Style */}
          <View style={styles.segmentSection}>
            <View style={styles.rowLeft}>
              <View style={[styles.iconWrap, { backgroundColor: colors.muted }]}>
                <Zap size={15} color={colors.textSecondary} />
              </View>
              <Text style={[styles.rowLabel, { color: colors.textPrimary }]}>Negotiation Style</Text>
            </View>
            <View style={[styles.segmented, { backgroundColor: colors.muted }]}>
              {(['aggressive', 'moderate', 'passive'] as const).map(s => {
                const active = negotiationStyle === s;
                return (
                  <TouchableOpacity
                    key={s}
                    style={[styles.segBtn, active && { backgroundColor: colors.surface }]}
                    onPress={() => handleNegotiationChange(s)}
                  >
                    <Text style={[styles.segText, { color: active ? colors.textPrimary : colors.textMuted }, active && styles.segTextActive]}>
                      {s.charAt(0).toUpperCase() + s.slice(1)}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </View>
          </View>

          <View style={[styles.divider, { backgroundColor: colors.divider }]} />

          {/* Reply Tone */}
          <View style={styles.segmentSection}>
            <View style={styles.rowLeft}>
              <View style={[styles.iconWrap, { backgroundColor: colors.muted }]}>
                <Mic size={15} color={colors.textSecondary} />
              </View>
              <Text style={[styles.rowLabel, { color: colors.textPrimary }]}>Reply Tone</Text>
            </View>
            <View style={[styles.segmented, { backgroundColor: colors.muted }]}>
              {(['professional', 'casual', 'firm'] as const).map(t => {
                const active = replyTone === t;
                return (
                  <TouchableOpacity
                    key={t}
                    style={[styles.segBtn, active && { backgroundColor: colors.surface }]}
                    onPress={() => handleToneChange(t)}
                  >
                    <Text style={[styles.segText, { color: active ? colors.textPrimary : colors.textMuted }, active && styles.segTextActive]}>
                      {t.charAt(0).toUpperCase() + t.slice(1)}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </View>
          </View>
        </View>
        <View style={styles.sectionHeader}>
          <Text style={[styles.sectionTitle, { color: colors.textMuted }]}>BACKEND AGENTS</Text>
        </View>
        <View style={[styles.card, { backgroundColor: colors.surface }]}>
          <View style={styles.row}>
            <View style={styles.rowLeft}>
              <View style={[styles.iconWrap, { backgroundColor: backendStatus === 'ok' ? '#D1FAE5' : colors.muted }]}>
                <Zap size={15} color={backendStatus === 'ok' ? '#059669' : colors.textSecondary} />
              </View>
              <Text style={[styles.rowLabel, { color: colors.textPrimary }]}>Backend Status</Text>
            </View>
            <Text style={[styles.rowValue, { color: backendStatus === 'ok' ? '#059669' : colors.textMuted }]}>
              {backendStatus === 'ok' ? 'Connected' : backendStatus === 'offline' ? 'Offline' : 'Checking...'}
            </Text>
          </View>
          {agents.map((agent, idx) => (
            <React.Fragment key={agent.slug}>
              <View style={[styles.divider, { backgroundColor: colors.divider }]} />
              <View style={styles.row}>
                <View style={styles.rowLeft}>
                  <View style={[styles.iconWrap, { backgroundColor: colors.muted }]}>
                    <Zap size={15} color={colors.textSecondary} />
                  </View>
                  <Text style={[styles.rowLabel, { color: colors.textPrimary }]}>{agent.name}</Text>
                </View>
                <Text style={[styles.rowValue, { color: colors.textMuted }]}>:{agent.port}</Text>
              </View>
            </React.Fragment>
          ))}
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
  rowValue: { fontSize: 14 },
  iconWrap: { width: 28, height: 28, borderRadius: 7, alignItems: 'center', justifyContent: 'center' },
  segmentSection: { paddingHorizontal: 14, paddingVertical: 13, gap: 10 },
  segmented: { flexDirection: 'row', borderRadius: 8, padding: 2, gap: 2 },
  segBtn: { flex: 1, alignItems: 'center', paddingVertical: 7, borderRadius: 6 },
  segText: { fontSize: 12, fontWeight: '500' },
  segTextActive: { fontWeight: '700' },
});
