import React, { useState, useEffect, useRef } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity, Switch, Alert, Image,
  Animated, ActivityIndicator, TextInput,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, router } from 'expo-router';
import { ArrowLeft, ChevronRight, ChevronLeft, Plus, X, Check } from 'lucide-react-native';
import { useTheme } from '../../contexts/ThemeContext';
import { useAuth } from '../../contexts/AuthContext';
import { supabase } from '../../lib/supabase';
import { pickImage } from '../../lib/imagePicker';
import { emit } from '../../lib/events';
import { PLATFORM_NAMES, MarketData, Conversation } from '../../data/mockData';
import type { Platform, NegotiationStyle, ReplyTone } from '../../lib/types';

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

// ---- Constants for picker options ----

const CONDITION_OPTIONS = ['New', 'Like New', 'Good', 'Fair', 'Poor'];
const NEGOTIATION_OPTIONS: NegotiationStyle[] = ['moderate', 'aggressive', 'passive'];
const REPLY_TONE_OPTIONS: ReplyTone[] = ['professional', 'casual', 'firm'];
const RESPONSE_DELAY_OPTIONS = ['1 min', '5 min', '15 min', '30 min', '1 hr'];
const ALL_PLATFORMS: Platform[] = ['ebay', 'depop', 'mercari', 'offerup', 'facebook'];

interface ItemDetail {
  id: string;
  type: 'buy' | 'sell';
  name: string;
  description: string;
  condition: string;
  autoAcceptThreshold?: number;
  initialPrice?: number;
  bestOffer?: number;
  status: string;
  quantity: number;
  negotiationStyle: string;
  replyTone: string;
  responseDelay: string;
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
    autoAcceptThreshold: row.auto_accept_threshold ?? undefined,
    initialPrice: row.initial_price ?? undefined,
    bestOffer: row.best_offer ?? undefined,
    status: row.status ?? 'active',
    quantity: row.quantity ?? 1,
    negotiationStyle: row.negotiation_style ?? 'moderate',
    replyTone: row.reply_tone ?? 'professional',
    responseDelay: row.response_delay ?? '5 min',
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
  const userToggledRef = React.useRef(false);

  // Inline-edit state
  const [editingField, setEditingField] = useState<string | null>(null);
  const [savingField, setSavingField] = useState<string | null>(null);
  const debounceTimers = useRef<Record<string, ReturnType<typeof setTimeout>>>({});

  useEffect(() => {
    if (!id) return;
    loadItem();
  }, [id]);

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

  // ---- Auto-save helpers ----

  async function updateField(field: string, value: any) {
    setSavingField(field);
    const { error } = await supabase.from('items').update({ [field]: value }).eq('id', id);
    if (error) console.error(`Failed to update ${field}:`, error.message);
    // Brief indicator
    setTimeout(() => setSavingField(prev => prev === field ? null : prev), 600);
  }

  async function updatePlatforms(platforms: string[]) {
    setSavingField('platforms');
    await supabase.from('item_platforms').delete().eq('item_id', id);
    if (platforms.length > 0) {
      await supabase.from('item_platforms').insert(platforms.map(p => ({ item_id: id, platform: p })));
    }
    setTimeout(() => setSavingField(prev => prev === 'platforms' ? null : prev), 600);
  }

  function updateFieldDebounced(field: string, value: any) {
    if (debounceTimers.current[field]) clearTimeout(debounceTimers.current[field]);
    debounceTimers.current[field] = setTimeout(() => {
      updateField(field, value);
    }, 800);
  }

  function handleTextChange(field: string, dbField: string, value: string) {
    if (!item) return;
    setItem({ ...item, [field]: value });
    updateFieldDebounced(dbField, value);
  }

  function handleNumberChange(field: string, dbField: string, value: string) {
    if (!item) return;
    const num = value === '' ? null : parseFloat(value);
    setItem({ ...item, [field]: num ?? undefined });
    updateFieldDebounced(dbField, num);
  }

  function handlePickerChange(field: string, dbField: string, value: string) {
    if (!item) return;
    setItem({ ...item, [field]: value });
    setEditingField(null);
    updateField(dbField, value);
  }

  function handlePlatformToggle(platform: string) {
    if (!item) return;
    const newPlatforms = item.platforms.includes(platform)
      ? item.platforms.filter(p => p !== platform)
      : [...item.platforms, platform];
    setItem({ ...item, platforms: newPlatforms });
    updatePlatforms(newPlatforms);
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

  async function handleAiToggle(value: boolean) {
    const newStatus = value ? 'active' : 'paused';
    userToggledRef.current = true;
    setAiActive(value);
    emit('item:statusChanged', id, newStatus);
    const { error } = await supabase.from('items').update({ status: newStatus }).eq('id', id);
    if (error) {
      console.error('Failed to update item status:', error.message);
      setAiActive(!value);
    }
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
          text: 'Delete', style: 'destructive', onPress: async () => {
            await supabase.from('agent_runs').delete().eq('item_id', id);
            const { error } = await supabase.from('items').delete().eq('id', id);
            if (error) {
              Alert.alert('Error', `Failed to delete item: ${error.message}`);
              return;
            }
            emit('item:deleted', id);
            router.back();
          }
        },
      ]
    );
  }

  const modeLabel = item?.type === 'buy' ? 'Buying' : 'Selling';

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
            <Text style={[styles.heroMetricLabel, { color: colors.textMuted }]}>INITIAL</Text>
            <Text style={[styles.heroMetricValue, { color: colors.textPrimary }]}>
              {item.initialPrice != null ? `$${item.initialPrice}` : '--'}
            </Text>
          </View>
        </View>
      </View>

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
        style={{ backgroundColor: colors.background }}
        keyboardShouldPersistTaps="handled"
      >
        {/* 1. Photos gallery */}
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

        {/* 2. Item Details section */}
        <View style={styles.sectionLarge}>
          <Text style={[styles.sectionLabel, { color: colors.textMuted }]}>ITEM DETAILS</Text>
          <View style={[styles.cardBody, { backgroundColor: colors.surface }]}>
            {/* Name */}
            <EditableTextField
              label="Name"
              value={item.name}
              field="name"
              dbField="name"
              colors={colors}
              editingField={editingField}
              savingField={savingField}
              onStartEdit={setEditingField}
              onChange={handleTextChange}
              onEndEdit={() => setEditingField(null)}
            />
            <View style={[styles.divider, { backgroundColor: colors.divider }]} />

            {/* Description */}
            <EditableTextField
              label="Description"
              value={item.description}
              field="description"
              dbField="description"
              colors={colors}
              editingField={editingField}
              savingField={savingField}
              onStartEdit={setEditingField}
              onChange={handleTextChange}
              onEndEdit={() => setEditingField(null)}
              multiline
            />
            <View style={[styles.divider, { backgroundColor: colors.divider }]} />

            {/* Condition */}
            <EditablePickerField
              label="Condition"
              value={item.condition}
              field="condition"
              dbField="condition"
              options={CONDITION_OPTIONS}
              colors={colors}
              editingField={editingField}
              savingField={savingField}
              onStartEdit={setEditingField}
              onChange={handlePickerChange}
            />
            <View style={[styles.divider, { backgroundColor: colors.divider }]} />

            {/* Quantity */}
            <EditableNumberField
              label="Quantity"
              value={item.quantity}
              field="quantity"
              dbField="quantity"
              colors={colors}
              editingField={editingField}
              savingField={savingField}
              onStartEdit={setEditingField}
              onChange={handleNumberChange}
              onEndEdit={() => setEditingField(null)}
            />
          </View>
        </View>

        {/* 3. Pricing section */}
        <View style={styles.sectionLarge}>
          <Text style={[styles.sectionLabel, { color: colors.textMuted }]}>PRICING</Text>
          <View style={[styles.cardBody, { backgroundColor: colors.surface }]}>
            {/* Initial Price */}
            <EditableNumberField
              label="Initial Price"
              value={item.initialPrice}
              field="initialPrice"
              dbField="initial_price"
              colors={colors}
              editingField={editingField}
              savingField={savingField}
              onStartEdit={setEditingField}
              onChange={handleNumberChange}
              onEndEdit={() => setEditingField(null)}
              prefix="$"
              placeholder="Not set"
            />
            <View style={[styles.divider, { backgroundColor: colors.divider }]} />

            {/* Auto-Accept Threshold */}
            <EditableNumberField
              label="Auto-Accept Threshold"
              value={item.autoAcceptThreshold}
              field="autoAcceptThreshold"
              dbField="auto_accept_threshold"
              colors={colors}
              editingField={editingField}
              savingField={savingField}
              onStartEdit={setEditingField}
              onChange={handleNumberChange}
              onEndEdit={() => setEditingField(null)}
              prefix="$"
              placeholder="Not set"
            />
          </View>
        </View>

        {/* 4. Agent Settings section */}
        <View style={styles.sectionLarge}>
          <Text style={[styles.sectionLabel, { color: colors.textMuted }]}>AGENT SETTINGS</Text>
          <View style={[styles.cardBody, { backgroundColor: colors.surface }]}>
            {/* Negotiation Style */}
            <SegmentedField
              label="Negotiation Style"
              value={item.negotiationStyle}
              field="negotiationStyle"
              dbField="negotiation_style"
              options={NEGOTIATION_OPTIONS}
              colors={colors}
              savingField={savingField}
              onChange={handlePickerChange}
            />
            <View style={[styles.divider, { backgroundColor: colors.divider }]} />

            {/* Reply Tone */}
            <SegmentedField
              label="Reply Tone"
              value={item.replyTone}
              field="replyTone"
              dbField="reply_tone"
              options={REPLY_TONE_OPTIONS}
              colors={colors}
              savingField={savingField}
              onChange={handlePickerChange}
            />
            <View style={[styles.divider, { backgroundColor: colors.divider }]} />

            {/* Response Delay */}
            <EditablePickerField
              label="Response Delay"
              value={item.responseDelay}
              field="responseDelay"
              dbField="response_delay"
              options={RESPONSE_DELAY_OPTIONS}
              colors={colors}
              editingField={editingField}
              savingField={savingField}
              onStartEdit={setEditingField}
              onChange={handlePickerChange}
            />
          </View>
        </View>

        {/* 5. Platforms section */}
        <View style={styles.sectionLarge}>
          <Text style={[styles.sectionLabel, { color: colors.textMuted }]}>PLATFORMS</Text>
          <View style={[styles.cardBody, { backgroundColor: colors.surface }]}>
            {ALL_PLATFORMS.map((platform, idx) => (
              <React.Fragment key={platform}>
                {idx > 0 && <View style={[styles.divider, { backgroundColor: colors.divider }]} />}
                <TouchableOpacity
                  style={styles.platformRow}
                  onPress={() => handlePlatformToggle(platform)}
                  activeOpacity={0.7}
                >
                  <Text style={[styles.platformLabel, { color: colors.textPrimary }]}>
                    {PLATFORM_NAMES[platform as keyof typeof PLATFORM_NAMES] ?? platform}
                  </Text>
                  <View style={styles.platformRight}>
                    {savingField === 'platforms' && (
                      <ActivityIndicator size="small" color={colors.accent} style={{ marginRight: 6 }} />
                    )}
                    <View style={[
                      styles.checkBox,
                      { borderColor: item.platforms.includes(platform) ? colors.accent : colors.muted },
                      item.platforms.includes(platform) && { backgroundColor: colors.accent },
                    ]}>
                      {item.platforms.includes(platform) && (
                        <Check size={14} color={colors.white} />
                      )}
                    </View>
                  </View>
                </TouchableOpacity>
              </React.Fragment>
            ))}
          </View>
        </View>

        {/* 6. Market Overview */}
        <View style={styles.sectionLarge}>
          <Text style={[styles.sectionLabel, { color: colors.textMuted }]}>MARKET OVERVIEW</Text>
        </View>
        {item.marketData.length === 0 ? (
          <View style={[styles.cardBody, { backgroundColor: colors.surface, marginHorizontal: 16 }]}>
            <Text style={[styles.emptyText, { color: colors.textMuted }]}>
              No market data yet. Run an agent to populate.
            </Text>
          </View>
        ) : (
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.marketScroll}
          >
            {item.marketData.map(md => (
              <MarketCard key={md.platform} data={md} />
            ))}
          </ScrollView>
        )}

        {/* 7. Conversations */}
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

        {/* 8. Delete */}
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

// ---- Editable field sub-components ----

function SaveIndicator({ visible, colors }: { visible: boolean; colors: any }) {
  if (!visible) return null;
  return (
    <View style={editStyles.saveIndicator}>
      <Check size={12} color={colors.accent} />
    </View>
  );
}

function EditableTextField({
  label, value, field, dbField, colors, editingField, savingField,
  onStartEdit, onChange, onEndEdit, multiline,
}: {
  label: string; value: string; field: string; dbField: string; colors: any;
  editingField: string | null; savingField: string | null;
  onStartEdit: (f: string) => void; onChange: (field: string, dbField: string, val: string) => void;
  onEndEdit: () => void; multiline?: boolean;
}) {
  const isEditing = editingField === field;
  const isSaving = savingField === dbField;

  if (isEditing) {
    return (
      <View style={editStyles.fieldContainer}>
        <Text style={[editStyles.fieldLabel, { color: colors.textMuted }]}>{label}</Text>
        <TextInput
          style={[
            editStyles.textInput,
            { color: colors.textPrimary, backgroundColor: colors.surfaceRaised, borderColor: colors.accent },
            multiline && { minHeight: 72, textAlignVertical: 'top' },
          ]}
          value={value}
          onChangeText={(text) => onChange(field, dbField, text)}
          onBlur={onEndEdit}
          autoFocus
          multiline={multiline}
          returnKeyType={multiline ? 'default' : 'done'}
          blurOnSubmit={!multiline}
          placeholderTextColor={colors.textMuted}
        />
      </View>
    );
  }

  return (
    <TouchableOpacity
      style={editStyles.fieldContainer}
      onPress={() => onStartEdit(field)}
      activeOpacity={0.7}
    >
      <View style={editStyles.fieldRow}>
        <Text style={[editStyles.fieldLabel, { color: colors.textMuted }]}>{label}</Text>
        <SaveIndicator visible={isSaving} colors={colors} />
      </View>
      <Text style={[editStyles.fieldValue, { color: colors.textPrimary }]}>
        {value || 'Tap to edit'}
      </Text>
    </TouchableOpacity>
  );
}

function EditableNumberField({
  label, value, field, dbField, colors, editingField, savingField,
  onStartEdit, onChange, onEndEdit, prefix, placeholder,
}: {
  label: string; value?: number; field: string; dbField: string; colors: any;
  editingField: string | null; savingField: string | null;
  onStartEdit: (f: string) => void; onChange: (field: string, dbField: string, val: string) => void;
  onEndEdit: () => void; prefix?: string; placeholder?: string;
}) {
  const isEditing = editingField === field;
  const isSaving = savingField === dbField;
  const displayValue = value != null ? `${prefix ?? ''}${value}` : (placeholder ?? 'Not set');

  if (isEditing) {
    return (
      <View style={editStyles.fieldContainer}>
        <Text style={[editStyles.fieldLabel, { color: colors.textMuted }]}>{label}</Text>
        <View style={editStyles.numberInputRow}>
          {prefix && <Text style={[editStyles.numberPrefix, { color: colors.textMuted }]}>{prefix}</Text>}
          <TextInput
            style={[
              editStyles.textInput,
              editStyles.numberInput,
              { color: colors.textPrimary, backgroundColor: colors.surfaceRaised, borderColor: colors.accent },
            ]}
            value={value != null ? String(value) : ''}
            onChangeText={(text) => onChange(field, dbField, text)}
            onBlur={onEndEdit}
            autoFocus
            keyboardType="numeric"
            returnKeyType="done"
            blurOnSubmit
            placeholder="0"
            placeholderTextColor={colors.textMuted}
          />
        </View>
      </View>
    );
  }

  return (
    <TouchableOpacity
      style={editStyles.fieldContainer}
      onPress={() => onStartEdit(field)}
      activeOpacity={0.7}
    >
      <View style={editStyles.fieldRow}>
        <Text style={[editStyles.fieldLabel, { color: colors.textMuted }]}>{label}</Text>
        <SaveIndicator visible={isSaving} colors={colors} />
      </View>
      <Text style={[
        editStyles.fieldValue,
        { color: value != null ? colors.textPrimary : colors.textMuted },
        value != null && { fontVariant: ['tabular-nums'] as any },
      ]}>
        {displayValue}
      </Text>
    </TouchableOpacity>
  );
}

function EditablePickerField({
  label, value, field, dbField, options, colors, editingField, savingField,
  onStartEdit, onChange,
}: {
  label: string; value: string; field: string; dbField: string;
  options: string[]; colors: any;
  editingField: string | null; savingField: string | null;
  onStartEdit: (f: string) => void;
  onChange: (field: string, dbField: string, val: string) => void;
}) {
  const isEditing = editingField === field;
  const isSaving = savingField === dbField;

  return (
    <View>
      <TouchableOpacity
        style={editStyles.fieldContainer}
        onPress={() => onStartEdit(isEditing ? '' : field)}
        activeOpacity={0.7}
      >
        <View style={editStyles.fieldRow}>
          <Text style={[editStyles.fieldLabel, { color: colors.textMuted }]}>{label}</Text>
          <View style={editStyles.fieldRow}>
            <SaveIndicator visible={isSaving} colors={colors} />
            <Text style={[editStyles.fieldValue, { color: colors.textPrimary }]}>
              {value}
            </Text>
            <ChevronRight size={14} color={colors.textMuted} style={{ marginLeft: 4 }} />
          </View>
        </View>
      </TouchableOpacity>
      {isEditing && (
        <View style={[editStyles.pickerOptions, { backgroundColor: colors.surfaceRaised }]}>
          {options.map((opt) => (
            <TouchableOpacity
              key={opt}
              style={[
                editStyles.pickerOption,
                value === opt && { backgroundColor: colors.accent + '18' },
              ]}
              onPress={() => onChange(field, dbField, opt)}
              activeOpacity={0.7}
            >
              <Text style={[
                editStyles.pickerOptionText,
                { color: value === opt ? colors.accent : colors.textPrimary },
                value === opt && { fontWeight: '700' },
              ]}>
                {opt}
              </Text>
              {value === opt && <Check size={14} color={colors.accent} />}
            </TouchableOpacity>
          ))}
        </View>
      )}
    </View>
  );
}

function SegmentedField({
  label, value, field, dbField, options, colors, savingField, onChange,
}: {
  label: string; value: string; field: string; dbField: string;
  options: string[]; colors: any; savingField: string | null;
  onChange: (field: string, dbField: string, val: string) => void;
}) {
  const isSaving = savingField === dbField;

  return (
    <View style={editStyles.segmentContainer}>
      <View style={editStyles.fieldRow}>
        <Text style={[editStyles.segmentLabel, { color: colors.textPrimary }]}>{label}</Text>
        <SaveIndicator visible={isSaving} colors={colors} />
      </View>
      <View style={[editStyles.segmented, { backgroundColor: colors.muted }]}>
        {options.map((opt) => {
          const active = value === opt;
          return (
            <TouchableOpacity
              key={opt}
              style={[editStyles.segBtn, active && { backgroundColor: colors.surface }]}
              onPress={() => onChange(field, dbField, opt)}
            >
              <Text style={[
                editStyles.segText,
                { color: active ? colors.textPrimary : colors.textMuted },
                active && editStyles.segTextActive,
              ]}>
                {opt.charAt(0).toUpperCase() + opt.slice(1)}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>
    </View>
  );
}

// ---- Existing sub-components ----

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
  const initial = (conv.username || '?')[0].toUpperCase();
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

// ---- Styles for editable fields ----

const editStyles = StyleSheet.create({
  fieldContainer: { paddingHorizontal: 14, paddingVertical: 12 },
  fieldRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  fieldLabel: { fontSize: 11, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.3, marginBottom: 4 },
  fieldValue: { fontSize: 14, fontWeight: '600', lineHeight: 20 },
  textInput: { fontSize: 14, fontWeight: '500', borderWidth: 1, borderRadius: 8, paddingHorizontal: 12, paddingVertical: 10, marginTop: 4 },
  numberInputRow: { flexDirection: 'row', alignItems: 'center', marginTop: 4 },
  numberPrefix: { fontSize: 16, fontWeight: '600', marginRight: 4 },
  numberInput: { flex: 1 },
  saveIndicator: { width: 18, height: 18, borderRadius: 9, alignItems: 'center', justifyContent: 'center' },
  pickerOptions: { marginHorizontal: 14, borderRadius: 8, overflow: 'hidden', marginBottom: 8 },
  pickerOption: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 14, paddingVertical: 11 },
  pickerOptionText: { fontSize: 14, fontWeight: '500' },
  segmentContainer: { paddingHorizontal: 14, paddingVertical: 13, gap: 10 },
  segmentLabel: { fontSize: 15, fontWeight: '500' },
  segmented: { flexDirection: 'row', borderRadius: 8, padding: 2, gap: 2 },
  segBtn: { flex: 1, alignItems: 'center', paddingVertical: 7, borderRadius: 6 },
  segText: { fontSize: 12, fontWeight: '500' },
  segTextActive: { fontWeight: '700' },
});

// ---- Main styles ----

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
  platformRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 14, paddingVertical: 13 },
  platformLabel: { fontSize: 15, fontWeight: '500' },
  platformRight: { flexDirection: 'row', alignItems: 'center' },
  checkBox: { width: 22, height: 22, borderRadius: 6, borderWidth: 2, alignItems: 'center', justifyContent: 'center' },
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
