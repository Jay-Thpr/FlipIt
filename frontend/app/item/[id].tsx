import React, { useState, useEffect, useRef } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity, Switch, Alert, Image,
  Animated, ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, router } from 'expo-router';
import { ArrowLeft, ChevronRight, ChevronLeft, Plus, X } from 'lucide-react-native';
import { useTheme } from '../../contexts/ThemeContext';
import { useAuth } from '../../contexts/AuthContext';
import { supabase } from '../../lib/supabase';
import { pickImage } from '../../lib/imagePicker';
import { emit } from '../../lib/events';
import { PLATFORM_NAMES, MarketData, Conversation } from '../../data/mockData';
import { startSellRun, startBuyRun, getLatestRun, submitSellCorrection, submitListingDecision, AgentRunResult } from '../../lib/api';
import { connectToRunStream, SSEEvent } from '../../lib/sse';

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

interface ItemDetail {
  id: string;
  type: 'buy' | 'sell';
  name: string;
  description: string;
  condition: string;
  targetPrice: number;
  minPrice?: number;
  maxPrice?: number;
  autoAcceptThreshold?: number;
  initialPrice?: number;
  bestOffer?: number;
  status: string;
  quantity: number;
  negotiationStyle: string;
  replyTone: string;
  platforms: string[];
  photos: { id: string; url: string; sortOrder: number }[];
  marketData: MarketData[];
  conversations: Conversation[];
}

function mapDbToDetail(row: any): ItemDetail {
  return {
    id: row.id,
    type: row.type,
    name: row.name,
    description: row.description ?? '',
    condition: row.condition ?? 'Good',
    targetPrice: row.target_price ?? 0,
    minPrice: row.min_price ?? undefined,
    maxPrice: row.max_price ?? undefined,
    autoAcceptThreshold: row.auto_accept_threshold ?? undefined,
    initialPrice: row.initial_price ?? undefined,
    bestOffer: row.best_offer ?? undefined,
    status: row.status ?? 'active',
    quantity: row.quantity ?? 1,
    negotiationStyle: row.negotiation_style ?? 'moderate',
    replyTone: row.reply_tone ?? 'professional',
    platforms: row.item_platforms?.map((p: any) => p.platform) ?? [],
    photos: (row.item_photos ?? [])
      .sort((a: any, b: any) => a.sort_order - b.sort_order)
      .map((p: any) => ({ id: p.id, url: p.photo_url, sortOrder: p.sort_order })),
    marketData: (row.market_data ?? []).map((md: any) => ({
      platform: md.platform,
      bestBuyPrice: md.best_buy_price,
      bestSellPrice: md.best_sell_price,
      volume: md.volume,
    })),
    conversations: (row.conversations ?? []).map((c: any) => ({
      id: c.id,
      username: c.username,
      platform: c.platform,
      lastMessage: c.last_message ?? '',
      timestamp: c.last_message_at ? timeAgo(c.last_message_at) : '',
      unread: c.unread ?? false,
      messages: (c.messages ?? [])
        .sort((a: any, b: any) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
        .map((m: any) => ({
          id: m.id,
          sender: m.sender,
          text: m.text,
          timestamp: new Date(m.created_at).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' }),
        })),
    })),
  };
}

export default function ItemDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { colors } = useTheme();
  const { user } = useAuth();
  const [item, setItem] = useState<ItemDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [aiActive, setAiActive] = useState(false);
  const [photos, setPhotos] = useState<{ id: string; url: string; sortOrder: number }[]>([]);
  const [run, setRun] = useState<AgentRunResult | null>(null);
  const [runLoading, setRunLoading] = useState(false);
  const [agentSteps, setAgentSteps] = useState<{ name: string; status: string; summary?: string }[]>([]);
  const [runError, setRunError] = useState<string | null>(null);
  const stopStreamRef = useRef<(() => void) | null>(null);
  const userToggledRef = React.useRef(false);

  useEffect(() => {
    if (!id) return;
    loadItem();
  }, [id]);

  useEffect(() => {
    if (!id) return;
    getLatestRun(id).then(setRun).catch(() => {});
  }, [id]);

  useEffect(() => {
    return () => { stopStreamRef.current?.(); };
  }, []);

  async function loadItem() {
    const { data } = await supabase
      .from('items')
      .select(`*, item_platforms(platform), item_photos(id, photo_url, sort_order), market_data(platform, best_buy_price, best_sell_price, volume), conversations(id, username, platform, last_message, last_message_at, unread, messages(id, sender, text, created_at))`)
      .eq('id', id)
      .single();

    if (data) {
      const detail = mapDbToDetail(data);
      setItem(detail);
      if (!userToggledRef.current) {
        setAiActive(detail.status === 'active');
      }
      setPhotos(detail.photos);
      // Mark as viewed
      supabase.from('items').update({ last_viewed_at: new Date().toISOString() }).eq('id', id).then(({ error }) => {
        if (error) console.error('Failed to update last_viewed_at:', error.message);
      });
    }
    setLoading(false);
  }

  const photoOpacity = useRef(new Animated.Value(1)).current;

  if (loading) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: colors.background, justifyContent: 'center', alignItems: 'center' }]}>
        <ActivityIndicator size="large" color={colors.accent} />
      </SafeAreaView>
    );
  }

  if (!item) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]}>
        <Text style={{ padding: 24, color: colors.textMuted }}>Item not found.</Text>
      </SafeAreaView>
    );
  }

  function handleAiToggle(value: boolean) {
    const newStatus = value ? 'active' : 'paused';
    userToggledRef.current = true;
    setAiActive(value);
    emit('item:statusChanged', id, newStatus);
    supabase.from('items').update({ status: newStatus }).eq('id', id);
  }

  function movePhoto(index: number, direction: 'up' | 'down') {
    const newPhotos = [...photos];
    const targetIndex = direction === 'up' ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= newPhotos.length) return;
    Animated.sequence([
      Animated.timing(photoOpacity, { toValue: 0.5, duration: 80, useNativeDriver: true }),
      Animated.timing(photoOpacity, { toValue: 1, duration: 120, useNativeDriver: true }),
    ]).start();
    [newPhotos[index], newPhotos[targetIndex]] = [newPhotos[targetIndex], newPhotos[index]];
    setPhotos(newPhotos);
    // Update sort orders in DB
    newPhotos.forEach((p, i) => {
      supabase.from('item_photos').update({ sort_order: i }).eq('id', p.id);
    });
  }

  function removePhoto(index: number) {
    Alert.alert('Remove Photo', 'Are you sure you want to remove this photo?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Remove', style: 'destructive', onPress: async () => {
          const photo = photos[index];
          await supabase.from('item_photos').delete().eq('id', photo.id);
          setPhotos(p => p.filter((_, i) => i !== index));
        }
      },
    ]);
  }

  async function handleAddPhoto() {
    if (!user || !id) return;
    const uris = await pickImage({ shape: 'rectangle' });
    if (uris.length === 0) return;

    for (const uri of uris) {
      const ext = uri.split('.').pop()?.toLowerCase() || 'jpg';
      const fileName = `${Date.now()}.${ext}`;
      const path = `${user.id}/${id}/${fileName}`;

      const formData = new FormData();
      formData.append('', {
        uri,
        name: fileName,
        type: `image/${ext === 'jpg' ? 'jpeg' : ext}`,
      } as any);

      const { error: uploadError } = await supabase.storage
        .from('item-photos')
        .upload(path, formData, { contentType: 'multipart/form-data' });

      if (!uploadError) {
        const { data: urlData } = supabase.storage.from('item-photos').getPublicUrl(path);
        const { data: photoRow } = await supabase.from('item_photos').insert({
          item_id: id,
          photo_url: urlData.publicUrl,
          sort_order: photos.length,
        }).select().single();

        if (photoRow) {
          setPhotos(prev => [...prev, { id: photoRow.id, url: urlData.publicUrl, sortOrder: photos.length }]);
        }
      }
    }
  }

  function handleDelete() {
    Alert.alert(
      'Delete Item',
      'This will permanently delete this item and all its listings, photos, conversations, and market data. This cannot be undone.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete', style: 'destructive', onPress: () => {
            emit('item:deleted', id);
            supabase.from('items').delete().eq('id', id);
            router.back();
          }
        },
      ]
    );
  }

  async function handleStartRun() {
    if (!item || !id) return;
    setRunLoading(true);
    setRunError(null);
    setAgentSteps([]);
    try {
      let response;
      if (item.type === 'sell') {
        const imageUrls = photos.map(p => p.url);
        response = await startSellRun(id, { image_urls: imageUrls, notes: item.description });
      } else {
        response = await startBuyRun(id, { query: item.name, budget: item.targetPrice });
      }
      const runId = response.run_id || response.session_id;

      // Connect to SSE stream
      stopStreamRef.current = connectToRunStream(
        runId,
        (event: SSEEvent) => {
          if (event.event === 'agent_started') {
            setAgentSteps(prev => [...prev, { name: event.data.agent_name || event.data.step, status: 'running' }]);
          } else if (event.event === 'agent_completed') {
            setAgentSteps(prev => prev.map(s =>
              s.name === (event.data.agent_name || event.data.step)
                ? { ...s, status: 'completed', summary: event.data.summary }
                : s
            ));
          } else if (event.event === 'agent_error') {
            setAgentSteps(prev => prev.map(s =>
              s.name === (event.data.agent_name || event.data.step)
                ? { ...s, status: 'error', summary: event.data.error }
                : s
            ));
          } else if (event.event === 'pipeline_complete') {
            getLatestRun(id).then(setRun).catch(() => {});
          } else if (event.event === 'pipeline_failed') {
            setRunError(event.data.error || 'Pipeline failed');
          } else if (event.event === 'vision_low_confidence') {
            setRun(prev => prev ? { ...prev, status: 'running' as const, sell_listing_review: null } : prev);
            getLatestRun(id).then(setRun).catch(() => {});
          } else if (event.event === 'listing_review_required') {
            getLatestRun(id).then(setRun).catch(() => {});
          }
        },
        (err) => { setRunError(err.message); },
        () => { setRunLoading(false); },
      );
    } catch (err: any) {
      setRunError(err.message);
      setRunLoading(false);
    }
  }

  async function handleListingDecision(decision: 'confirm_submit' | 'revise' | 'abort', instructions?: string) {
    if (!run) return;
    try {
      await submitListingDecision(run.session_id, decision, instructions);
      getLatestRun(id!).then(setRun).catch(() => {});
    } catch (err: any) {
      Alert.alert('Error', err.message);
    }
  }

  const modeLabel = item.type === 'buy' ? 'Buying' : 'Selling';

  return (
    <SafeAreaView
      style={[styles.container, { backgroundColor: colors.surface }]}
      edges={['top']}
    >
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
            {item.name}
          </Text>
          <Text style={[styles.headerSubtitle, { color: colors.textMuted }]}>{modeLabel}</Text>
        </View>
        <Switch
          value={aiActive}
          onValueChange={handleAiToggle}
          trackColor={{ true: colors.accent, false: colors.muted }}
          thumbColor={colors.white}
        />
      </View>

      {/* Hero metrics */}
      <View style={[styles.heroStrip, { backgroundColor: colors.surface }]}>
        <View style={styles.heroContent}>
          <View style={[styles.heroMetricMain, { flex: 2 }]}>
            <Text style={[styles.heroMetricLabel, { color: colors.textMuted }]}>BEST OFFER</Text>
            <Text style={[styles.heroMainValue, { color: item.bestOffer ? colors.accent : colors.textPrimary }]}>
              {item.bestOffer ? `$${item.bestOffer}` : 'None'}
            </Text>
          </View>
          <View style={[styles.heroDivider, { backgroundColor: colors.divider }]} />
          <View style={styles.heroMetric}>
            <Text style={[styles.heroMetricLabel, { color: colors.textMuted }]}>TARGET</Text>
            <Text style={[styles.heroMetricValue, { color: colors.textPrimary }]}>
              ${item.targetPrice}
            </Text>
          </View>
        </View>
      </View>

      {/* Agent Run Section */}
      {!run || run.status === 'completed' || run.status === 'failed' ? (
        <View style={{ paddingHorizontal: 16, paddingVertical: 12 }}>
          <TouchableOpacity
            style={{
              backgroundColor: colors.accent,
              borderRadius: 12,
              paddingVertical: 14,
              alignItems: 'center',
              opacity: runLoading ? 0.6 : 1,
            }}
            onPress={handleStartRun}
            disabled={runLoading}
            activeOpacity={0.7}
          >
            <Text style={{ color: '#FFFFFF', fontSize: 16, fontWeight: '700' }}>
              {runLoading ? 'Starting...' : item.type === 'sell' ? '🔍 Start Selling' : '🛒 Start Buying'}
            </Text>
          </TouchableOpacity>
          {runError && (
            <Text style={{ color: colors.destructive, fontSize: 13, marginTop: 8, textAlign: 'center' }}>{runError}</Text>
          )}
        </View>
      ) : null}

      {/* Agent Steps Progress */}
      {agentSteps.length > 0 && (
        <View style={{ paddingHorizontal: 16, paddingBottom: 8 }}>
          <Text style={[styles.sectionLabel, { color: colors.textMuted, paddingHorizontal: 4 }]}>AGENT PROGRESS</Text>
          <View style={[styles.cardBody, { backgroundColor: colors.surface }]}>
            {agentSteps.map((step, idx) => (
              <View key={idx}>
                {idx > 0 && <View style={[styles.divider, { backgroundColor: colors.divider }]} />}
                <View style={{ flexDirection: 'row', alignItems: 'center', paddingHorizontal: 14, paddingVertical: 10, gap: 10 }}>
                  <Text style={{ fontSize: 14 }}>
                    {step.status === 'running' ? '⏳' : step.status === 'completed' ? '✅' : '❌'}
                  </Text>
                  <View style={{ flex: 1 }}>
                    <Text style={{ color: colors.textPrimary, fontSize: 14, fontWeight: '600' }}>
                      {step.name?.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                    </Text>
                    {step.summary && (
                      <Text style={{ color: colors.textMuted, fontSize: 12, marginTop: 2 }} numberOfLines={2}>
                        {step.summary}
                      </Text>
                    )}
                  </View>
                </View>
              </View>
            ))}
          </View>
        </View>
      )}

      {/* Sell Listing Review */}
      {run?.sell_listing_review && run.status === 'running' && (
        <View style={{ paddingHorizontal: 16, paddingBottom: 8 }}>
          <Text style={[styles.sectionLabel, { color: colors.textMuted, paddingHorizontal: 4 }]}>LISTING REVIEW</Text>
          <View style={[styles.cardBody, { backgroundColor: colors.surface, padding: 14 }]}>
            <Text style={{ color: colors.textPrimary, fontSize: 15, fontWeight: '600', marginBottom: 8 }}>
              Review your listing before posting
            </Text>
            {run.sell_listing_review.listing_preview && (
              <View style={{ gap: 4, marginBottom: 12 }}>
                <Text style={{ color: colors.textMuted, fontSize: 12 }}>Title: {run.sell_listing_review.listing_preview.title}</Text>
                <Text style={{ color: colors.textMuted, fontSize: 12 }}>Price: ${run.sell_listing_review.listing_preview.price}</Text>
                {run.sell_listing_review.listing_preview.description && (
                  <Text style={{ color: colors.textMuted, fontSize: 12 }} numberOfLines={3}>
                    {run.sell_listing_review.listing_preview.description}
                  </Text>
                )}
              </View>
            )}
            <View style={{ flexDirection: 'row', gap: 8 }}>
              <TouchableOpacity
                style={{ flex: 1, backgroundColor: colors.accent, borderRadius: 8, paddingVertical: 10, alignItems: 'center' }}
                onPress={() => handleListingDecision('confirm_submit')}
              >
                <Text style={{ color: '#FFFFFF', fontWeight: '700', fontSize: 14 }}>Confirm & Post</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={{ flex: 1, backgroundColor: colors.muted, borderRadius: 8, paddingVertical: 10, alignItems: 'center' }}
                onPress={() => handleListingDecision('abort')}
              >
                <Text style={{ color: colors.textPrimary, fontWeight: '600', fontSize: 14 }}>Abort</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      )}

      {/* Buy Results */}
      {run?.status === 'completed' && run.pipeline === 'buy' && run.result?.outputs && (
        <View style={{ paddingHorizontal: 16, paddingBottom: 8 }}>
          <Text style={[styles.sectionLabel, { color: colors.textMuted, paddingHorizontal: 4 }]}>SEARCH RESULTS</Text>
          <View style={[styles.cardBody, { backgroundColor: colors.surface, padding: 14 }]}>
            {run.result.outputs.ranking?.top_choice && (
              <View style={{ marginBottom: 8 }}>
                <Text style={{ color: colors.accent, fontSize: 14, fontWeight: '700' }}>Top Choice</Text>
                <Text style={{ color: colors.textPrimary, fontSize: 16, fontWeight: '800', marginTop: 2 }}>
                  ${run.result.outputs.ranking.top_choice.price} — {run.result.outputs.ranking.top_choice.platform}
                </Text>
                {run.result.outputs.ranking.top_choice.seller && (
                  <Text style={{ color: colors.textMuted, fontSize: 12 }}>Seller: {run.result.outputs.ranking.top_choice.seller}</Text>
                )}
              </View>
            )}
            {run.result.outputs.negotiation?.offers && (
              <View>
                <Text style={{ color: colors.textMuted, fontSize: 11, fontWeight: '600', letterSpacing: 0.5, marginTop: 8, marginBottom: 4 }}>OFFERS SENT</Text>
                {run.result.outputs.negotiation.offers.map((offer: any, idx: number) => (
                  <View key={idx} style={{ flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 6 }}>
                    <Text style={{ color: colors.textPrimary, fontSize: 13 }}>{offer.seller || offer.platform}</Text>
                    <Text style={{ color: offer.status === 'sent' ? colors.accent : colors.textMuted, fontSize: 13, fontWeight: '600' }}>
                      {offer.status === 'sent' ? '✓ Sent' : offer.status}
                    </Text>
                  </View>
                ))}
              </View>
            )}
          </View>
        </View>
      )}

      {/* Sell Results */}
      {run?.status === 'completed' && run.pipeline === 'sell' && run.result?.outputs && (
        <View style={{ paddingHorizontal: 16, paddingBottom: 8 }}>
          <Text style={[styles.sectionLabel, { color: colors.textMuted, paddingHorizontal: 4 }]}>SELL RESULTS</Text>
          <View style={[styles.cardBody, { backgroundColor: colors.surface, padding: 14 }]}>
            {run.result.outputs.pricing && (
              <View style={{ marginBottom: 8 }}>
                <Text style={{ color: colors.accent, fontSize: 14, fontWeight: '700' }}>Recommended Price</Text>
                <Text style={{ color: colors.textPrimary, fontSize: 24, fontWeight: '800', marginTop: 2 }}>
                  ${run.result.outputs.pricing.recommended_list_price || run.result.outputs.pricing.recommended_price}
                </Text>
                {run.result.outputs.pricing.profit_margin != null && (
                  <Text style={{ color: colors.accent, fontSize: 14, marginTop: 2 }}>
                    Profit margin: ${run.result.outputs.pricing.profit_margin}
                  </Text>
                )}
              </View>
            )}
            {run.result.outputs.ebay_sold_comps && (
              <Text style={{ color: colors.textMuted, fontSize: 12 }}>
                Based on {run.result.outputs.ebay_sold_comps.sample_size || '?'} eBay sold comps
              </Text>
            )}
          </View>
        </View>
      )}

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
        style={{ backgroundColor: colors.background }}
      >
        {/* Photos gallery */}
        <View style={styles.section}>
          <View style={styles.photoHeaderRow}>
            <Text style={[styles.sectionLabel, { color: colors.textMuted }]}>
              PHOTOS ({photos.length})
            </Text>
            <TouchableOpacity
              style={[styles.addPhotoBtn, { backgroundColor: colors.surfaceRaised }]}
              onPress={handleAddPhoto}
              hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
              accessibilityLabel="Add photo"
            >
              <Plus size={16} color={colors.textPrimary} />
              <Text style={[styles.addPhotoBtnText, { color: colors.textPrimary }]}>Add</Text>
            </TouchableOpacity>
          </View>
          {photos.length === 0 ? (
            <TouchableOpacity
              style={[styles.emptyPhotos, { backgroundColor: colors.surface }]}
              onPress={handleAddPhoto}
              activeOpacity={0.7}
            >
              <Plus size={24} color={colors.textMuted} />
              <Text style={[styles.emptyPhotosText, { color: colors.textMuted }]}>
                Add photos for your listing
              </Text>
              <Text style={[styles.emptyPhotosHint, { color: colors.textMuted }]}>
                First photo is the cover image
              </Text>
            </TouchableOpacity>
          ) : (
            <Animated.View style={{ opacity: photoOpacity }}>
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.photoScroll}
            >
              {photos.map((photo, idx) => (
                <View key={photo.id} style={[styles.photoCard, { backgroundColor: colors.surface }]}>
                  <View style={styles.photoImageWrap}>
                    <Image source={{ uri: photo.url }} style={styles.photoImage} resizeMode="cover" />
                    <View style={styles.photoBadge}>
                      <Text style={styles.photoBadgeText}>{idx + 1}</Text>
                    </View>
                    <TouchableOpacity
                      style={styles.photoDeleteBtn}
                      onPress={() => removePhoto(idx)}
                      hitSlop={{ top: 4, bottom: 4, left: 4, right: 4 }}
                      accessibilityLabel="Remove photo"
                    >
                      <X size={14} color="#FFFFFF" />
                    </TouchableOpacity>
                  </View>
                  <View style={styles.photoReorderRow}>
                    <TouchableOpacity
                      onPress={() => movePhoto(idx, 'up')}
                      disabled={idx === 0}
                      style={[styles.reorderBtn, { backgroundColor: colors.surfaceRaised, opacity: idx === 0 ? 0.3 : 1 }]}
                      hitSlop={{ top: 4, bottom: 4, left: 4, right: 4 }}
                    >
                      <ChevronLeft size={16} color={colors.textSecondary} />
                    </TouchableOpacity>
                    <TouchableOpacity
                      onPress={() => movePhoto(idx, 'down')}
                      disabled={idx === photos.length - 1}
                      style={[styles.reorderBtn, { backgroundColor: colors.surfaceRaised, opacity: idx === photos.length - 1 ? 0.3 : 1 }]}
                      hitSlop={{ top: 4, bottom: 4, left: 4, right: 4 }}
                    >
                      <ChevronRight size={16} color={colors.textSecondary} />
                    </TouchableOpacity>
                  </View>
                </View>
              ))}
            </ScrollView>
            </Animated.View>
          )}
        </View>

        {/* Details card */}
        <View style={styles.sectionLarge}>
          <Text style={[styles.sectionLabel, { color: colors.textMuted }]}>DETAILS</Text>
          <View style={[styles.cardBody, { backgroundColor: colors.surface }]}>
            <View style={styles.descriptionBlock}>
              <Text style={[styles.descriptionValue, { color: colors.textPrimary }]}>
                {item.description}
              </Text>
            </View>
            <View style={[styles.divider, { backgroundColor: colors.divider }]} />
            <View style={styles.infoGrid}>
              <InfoCell label="Condition" value={item.condition} colors={colors} />
              <InfoCell label="Quantity" value={`${item.quantity}`} colors={colors} />
              <InfoCell label="Negotiation" value={item.negotiationStyle.charAt(0).toUpperCase() + item.negotiationStyle.slice(1)} colors={colors} />
              <InfoCell label="Tone" value={item.replyTone.charAt(0).toUpperCase() + item.replyTone.slice(1)} colors={colors} />
            </View>
            <View style={[styles.divider, { backgroundColor: colors.divider }]} />
            {item.initialPrice != null && <SettingRow label="Initial Price" value={`$${item.initialPrice}`} colors={colors} />}
            <SettingRow label="Target Price" value={`$${item.targetPrice}`} colors={colors} />
            {item.minPrice != null && <SettingRow label="Min Acceptable" value={`$${item.minPrice}`} colors={colors} />}
            {item.maxPrice != null && <SettingRow label="Max Acceptable" value={`$${item.maxPrice}`} colors={colors} />}
            {item.autoAcceptThreshold != null && <SettingRow label="Auto-Accept" value={`$${item.autoAcceptThreshold}`} colors={colors} />}
            <View style={[styles.divider, { backgroundColor: colors.divider }]} />
            <SettingRow label="Platforms" value={item.platforms.map(p => PLATFORM_NAMES[p as keyof typeof PLATFORM_NAMES] ?? p).join(', ')} colors={colors} />
          </View>
        </View>

        {/* Market Overview */}
        <View style={styles.sectionLarge}>
          <Text style={[styles.sectionLabel, { color: colors.textMuted }]}>MARKET OVERVIEW</Text>
        </View>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.marketScroll}
        >
          {item.marketData.map(md => (
            <MarketCard key={md.platform} data={md} />
          ))}
        </ScrollView>

        {/* Conversations */}
        <View style={styles.sectionLarge}>
          <Text style={[styles.sectionLabel, { color: colors.textMuted }]}>
            CONVERSATIONS ({item.conversations.length})
          </Text>
          <View style={[styles.cardBody, { backgroundColor: colors.surface }]}>
            {item.conversations.length === 0 ? (
              <Text style={[styles.emptyText, { color: colors.textMuted }]}>
                No active conversations yet.
              </Text>
            ) : (
              item.conversations.map((conv, idx) => (
                <React.Fragment key={conv.id}>
                  {idx > 0 && <View style={[styles.divider, { backgroundColor: colors.divider }]} />}
                  <ConvRow
                    conv={conv}
                    onPress={() => router.push(`/chat/${conv.id}?itemId=${item.id}`)}
                  />
                </React.Fragment>
              ))
            )}
          </View>
        </View>

        {/* Archive */}
        <TouchableOpacity
          style={styles.deleteBtn}
          onPress={handleDelete}
          activeOpacity={0.7}
        >
          <Text style={[styles.deleteBtnText, { color: colors.destructive }]}>
            Delete Item
          </Text>
        </TouchableOpacity>

        <View style={{ height: 32 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

// ─── Sub-components ────────────────────────────────────────────────────────────

function InfoCell({ label, value, colors }: { label: string; value: string; colors: any }) {
  return (
    <View style={styles.infoCell}>
      <Text style={[styles.infoCellLabel, { color: colors.textMuted }]}>{label}</Text>
      <Text style={[styles.infoCellValue, { color: colors.textPrimary }]}>{value}</Text>
    </View>
  );
}

function SettingRow({ label, value, colors }: { label: string; value: string; colors: any }) {
  return (
    <View style={styles.settingRow}>
      <Text style={[styles.settingLabel, { color: colors.textMuted }]}>{label}</Text>
      <Text style={[styles.settingValue, { color: colors.textPrimary }]}>{value}</Text>
    </View>
  );
}

function MarketCard({ data }: { data: MarketData }) {
  const { colors } = useTheme();
  return (
    <View style={[styles.marketCard, { backgroundColor: colors.surface }]}>
      <Text style={[styles.marketName, { color: colors.textPrimary }]}>{PLATFORM_NAMES[data.platform]}</Text>
      <View style={styles.marketPriceRow}>
        <View>
          <Text style={[styles.marketPriceLabel, { color: colors.textMuted }]}>Buy</Text>
          <Text style={[styles.marketPrice, { color: colors.textPrimary }]}>${data.bestBuyPrice}</Text>
        </View>
        <View style={[styles.marketDividerV, { backgroundColor: colors.divider }]} />
        <View>
          <Text style={[styles.marketPriceLabel, { color: colors.textMuted }]}>Sell</Text>
          <Text style={[styles.marketPrice, { color: colors.textPrimary }]}>${data.bestSellPrice}</Text>
        </View>
      </View>
      <Text style={[styles.volumeText, { color: colors.textMuted }]}>{data.volume} listings</Text>
    </View>
  );
}

function ConvRow({ conv, onPress }: { conv: Conversation; onPress: () => void }) {
  const { colors } = useTheme();
  const initial = conv.username[0].toUpperCase();
  return (
    <TouchableOpacity style={styles.convRow} onPress={onPress} activeOpacity={0.7}>
      <View style={[styles.convAvatar, { backgroundColor: colors.surfaceRaised }]}>
        <Text style={[styles.convAvatarText, { color: colors.textSecondary }]}>{initial}</Text>
      </View>
      <View style={styles.convInfo}>
        <View style={styles.convNameRow}>
          <Text style={[styles.convUsername, { color: colors.textPrimary }]}>{conv.username}</Text>
          <Text style={[styles.convPlatform, { color: colors.textMuted }]}>{PLATFORM_NAMES[conv.platform]}</Text>
        </View>
        <Text
          style={[
            styles.convPreview,
            { color: conv.unread ? colors.textPrimary : colors.textMuted },
            conv.unread && styles.convPreviewUnread,
          ]}
          numberOfLines={1}
        >
          {conv.lastMessage}
        </Text>
      </View>
      <View style={styles.convRight}>
        <Text style={[styles.convTime, { color: conv.unread ? colors.textPrimary : colors.textMuted }, conv.unread && styles.convTimeUnread]}>
          {conv.timestamp}
        </Text>
        <ChevronRight size={14} color={colors.textMuted} />
      </View>
    </TouchableOpacity>
  );
}

// ─── Styles ────────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 10, gap: 10 },
  backBtn: { width: 36, height: 36, alignItems: 'center', justifyContent: 'center' },
  headerCenter: { flex: 1, gap: 1 },
  headerTitle: { fontSize: 16, fontWeight: '700', letterSpacing: -0.2 },
  headerSubtitle: { fontSize: 12, fontWeight: '500' },
  heroStrip: { paddingBottom: 4 },
  heroContent: { flexDirection: 'row', alignItems: 'center', paddingVertical: 12, paddingHorizontal: 16 },
  heroMetricMain: { gap: 2 },
  heroMainValue: { fontSize: 28, fontWeight: '800', letterSpacing: -0.5, fontVariant: ['tabular-nums'] },
  heroMetric: { flex: 1, alignItems: 'center', gap: 2 },
  heroMetricLabel: { fontSize: 10, fontWeight: '600', letterSpacing: 0.6 },
  heroMetricValue: { fontSize: 18, fontWeight: '800', letterSpacing: -0.3, fontVariant: ['tabular-nums'] },
  heroDivider: { width: 1, height: 36, marginHorizontal: 16 },
  scrollContent: { paddingBottom: 48 },
  section: { marginHorizontal: 16, marginTop: 20 },
  sectionLarge: { marginHorizontal: 16, marginTop: 28 },
  sectionLabel: { fontSize: 11, fontWeight: '600', letterSpacing: 0.8, marginBottom: 8, paddingHorizontal: 4 },
  cardBody: { borderRadius: 12, overflow: 'hidden' },
  divider: { height: 1 },
  descriptionBlock: { paddingHorizontal: 14, paddingVertical: 14 },
  descriptionValue: { fontSize: 14, lineHeight: 21 },
  infoGrid: { flexDirection: 'row', flexWrap: 'wrap' },
  infoCell: { width: '50%', paddingHorizontal: 14, paddingVertical: 10, gap: 2 },
  infoCellLabel: { fontSize: 11, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.3 },
  infoCellValue: { fontSize: 14, fontWeight: '600' },
  settingRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 14, paddingVertical: 12 },
  settingLabel: { fontSize: 14, fontWeight: '500' },
  settingValue: { fontSize: 14, fontWeight: '600', maxWidth: '55%', textAlign: 'right', fontVariant: ['tabular-nums'] },
  marketScroll: { paddingHorizontal: 16, gap: 10, paddingBottom: 4 },
  marketCard: { borderRadius: 12, padding: 14, minWidth: 130, gap: 8 },
  marketName: { fontSize: 13, fontWeight: '700' },
  marketPriceRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  marketDividerV: { width: 1, height: 32 },
  marketPriceLabel: { fontSize: 10, fontWeight: '600', letterSpacing: 0.4, textTransform: 'uppercase', marginBottom: 2 },
  marketPrice: { fontSize: 18, fontWeight: '800', letterSpacing: -0.3, fontVariant: ['tabular-nums'] },
  volumeText: { fontSize: 11, fontWeight: '500' },
  emptyText: { fontSize: 14, textAlign: 'center', paddingVertical: 24 },
  convRow: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 14, paddingVertical: 12, gap: 10 },
  convAvatar: { width: 36, height: 36, borderRadius: 18, alignItems: 'center', justifyContent: 'center' },
  convAvatarText: { fontSize: 14, fontWeight: '700' },
  convInfo: { flex: 1, gap: 3 },
  convNameRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  convUsername: { fontSize: 14, fontWeight: '600' },
  convPlatform: { fontSize: 12 },
  convPreview: { fontSize: 13 },
  convPreviewUnread: { fontWeight: '500' },
  convRight: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  convTime: { fontSize: 11, fontVariant: ['tabular-nums'] },
  convTimeUnread: { fontWeight: '600' },
  photoHeaderRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 4, marginBottom: 8 },
  addPhotoBtn: { flexDirection: 'row', alignItems: 'center', gap: 4, borderRadius: 6, paddingHorizontal: 10, paddingVertical: 5 },
  addPhotoBtnText: { fontSize: 13, fontWeight: '600' },
  emptyPhotos: { borderRadius: 12, paddingVertical: 32, alignItems: 'center', gap: 8 },
  emptyPhotosText: { fontSize: 14, fontWeight: '500' },
  emptyPhotosHint: { fontSize: 12, textAlign: 'center', paddingHorizontal: 32 },
  photoScroll: { gap: 12, paddingBottom: 4 },
  photoCard: { borderRadius: 12, overflow: 'hidden', width: 150 },
  photoImageWrap: { width: 150, height: 150, position: 'relative' },
  photoImage: { width: 150, height: 150 },
  photoBadge: { position: 'absolute', bottom: 6, left: 6, backgroundColor: 'rgba(0,0,0,0.6)', borderRadius: 4, paddingHorizontal: 6, paddingVertical: 2 },
  photoBadgeText: { fontSize: 11, fontWeight: '700', color: '#FFFFFF', fontVariant: ['tabular-nums'] },
  photoDeleteBtn: { position: 'absolute', top: 6, right: 6, width: 28, height: 28, borderRadius: 14, backgroundColor: 'rgba(0,0,0,0.6)', alignItems: 'center', justifyContent: 'center' },
  photoReorderRow: { flexDirection: 'row', justifyContent: 'center', gap: 8, paddingVertical: 8 },
  reorderBtn: { width: 36, height: 32, borderRadius: 6, alignItems: 'center', justifyContent: 'center' },
  deleteBtn: { marginTop: 40, paddingVertical: 14, alignItems: 'center' },
  deleteBtnText: { fontSize: 14, fontWeight: '500' },
});
