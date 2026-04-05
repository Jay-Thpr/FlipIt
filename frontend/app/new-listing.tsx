import React, { useState } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity,
  TextInput, Switch, Alert, Image, KeyboardAvoidingView, Platform as RNPlatform,
  ActivityIndicator, Modal,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, router } from 'expo-router';
import { ArrowLeft, Plus, X, Check } from 'lucide-react-native';
import * as FileSystem from 'expo-file-system/legacy';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import { pickImage } from '../lib/imagePicker';
import { analyzeItemPhoto, generateWhiteBackgroundPhoto } from '../lib/gemini';
import { emit } from '../lib/events';
import { Platform, PLATFORM_NAMES, NegotiationStyle, ReplyTone, Item, MarketData, Conversation, addLocalItem } from '../data/mockData';

const ALL_PLATFORMS: Platform[] = ['ebay', 'depop', 'mercari', 'offerup', 'facebook'];
const CONDITIONS = ['New', 'Like New', 'Good', 'Fair', 'Poor'];

export default function NewListingScreen() {
  const { type } = useLocalSearchParams<{ type: string }>();
  const { colors } = useTheme();
  const { user } = useAuth();
  const listingType = type === 'buy' ? 'buy' : 'sell';

  // ─── Form State ─────────────────────────────────────────────────────────────
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [condition, setCondition] = useState('Good');
  const [quantity, setQuantity] = useState('1');
  const [targetPrice, setTargetPrice] = useState('');
  const [minPrice, setMinPrice] = useState('');
  const [maxPrice, setMaxPrice] = useState('');
  const [autoAcceptThreshold, setAutoAcceptThreshold] = useState('');
  const [initialPrice, setInitialPrice] = useState('');
  const [selectedPlatforms, setSelectedPlatforms] = useState<Platform[]>([...ALL_PLATFORMS]);
  const [negotiationStyle, setNegotiationStyle] = useState<NegotiationStyle>('moderate');
  const [replyTone, setReplyTone] = useState<ReplyTone>('professional');
  const [aiActive, setAiActive] = useState(true);
  const [photos, setPhotos] = useState<string[]>([]);
  const [creating, setCreating] = useState(false);
  const [processingPhoto, setProcessingPhoto] = useState(false);
  const [processingStep, setProcessingStep] = useState('');

  function togglePlatform(p: Platform) {
    setSelectedPlatforms(prev =>
      prev.includes(p) ? prev.filter(x => x !== p) : [...prev, p]
    );
  }

  async function handleAddPhoto() {
    const uris = await pickImage({ shape: 'rectangle', multiple: false });
    if (uris.length === 0) return;

    const originalUri = uris[0];

    // Show overlay FIRST — don't add any photo yet, freeze here
    setProcessingPhoto(true);
    setProcessingStep('Reading photo...');

    let finalPhotoUri = originalUri; // fallback is always the original

    try {
      // Step 1 — Read image as base64
      const base64 = await FileSystem.readAsStringAsync(originalUri, {
        encoding: 'base64' as any,
      });

      // Step 2 — Gemini Vision: identify the item & auto-fill form
      setProcessingStep('✨ Identifying item with Gemini Vision...');
      let analysis = null;
      try {
        analysis = await analyzeItemPhoto(base64, 'image/jpeg');
        if (analysis.name && !name.trim()) setName(analysis.name);
        if (analysis.description && !description.trim()) setDescription(analysis.description);
        if (analysis.condition) setCondition(analysis.condition);
      } catch (e) {
        console.warn('[Gemini Vision] failed:', e);
      }

      // Step 3 — Gemini Nano Banana: generate white-background product photo
      setProcessingStep('🖼️ Generating professional product photo...');
      const itemDesc = analysis?.name ?? 'secondhand fashion item';
      const cleanDataUri = await generateWhiteBackgroundPhoto(itemDesc, base64, 'image/jpeg');

      if (cleanDataUri) {
        finalPhotoUri = cleanDataUri; // use the pristine Gemini-generated image
      }
    } catch (e: any) {
      console.warn('[Nano Banana] pipeline error:', e.message);
    } finally {
      // Only NOW do we add the photo and dismiss the overlay
      setPhotos(prev => [...prev, finalPhotoUri]);
      setProcessingPhoto(false);
      setProcessingStep('');
    }
  }

  function removePhoto(idx: number) {
    setPhotos(prev => prev.filter((_, i) => i !== idx));
  }

  async function handleCreate() {
    if (!name.trim()) {
      Alert.alert('Missing Name', 'Please enter a listing name.');
      return;
    }
    if (!targetPrice.trim()) {
      Alert.alert('Missing Target Price', 'Please enter a target price.');
      return;
    }
    if (selectedPlatforms.length === 0) {
      Alert.alert('No Platforms', 'Please select at least one platform.');
      return;
    }
    /*
    if (!user) return;
    */

    setCreating(true);
    try {
      // 1. Generate unique ID
      const itemId = Math.random().toString(36).substring(7);

      // 2. Auto-generate mock data based on type
      const price = parseFloat(targetPrice);
      
      const mockMarketData: MarketData[] = selectedPlatforms.map(p => ({
        platform: p,
        bestBuyPrice: listingType === 'sell' ? price * 0.9 : price,
        bestSellPrice: listingType === 'sell' ? price : price * 1.1,
        volume: Math.floor(Math.random() * 50) + 5,
      }));

      const mockConversations: Conversation[] = [];
      
      if (listingType === 'sell') {
        // Buyer 1: Lowballer
        mockConversations.push({
          id: `c-${itemId}-1`,
          username: 'dealfinder_99',
          platform: selectedPlatforms[0],
          lastMessage: `Would you take $${(price * 0.7).toFixed(2)}?`,
          timestamp: '2m ago',
          unread: true,
          messages: [
            { id: 'm1', sender: 'them', text: 'Hi, I saw your listing. Is the price firm?', timestamp: '10:00 AM' },
            { id: 'm2', sender: 'agent', text: 'Hi! I am open to reasonable offers.', timestamp: '10:05 AM' },
            { id: 'm3', sender: 'them', text: `Would you take $${(price * 0.7).toFixed(2)}?`, timestamp: '10:10 AM' },
          ],
        });
        // Buyer 2: Serious Inquirer
        mockConversations.push({
          id: `c-${itemId}-2`,
          username: 'collector_pro',
          platform: selectedPlatforms[1] || selectedPlatforms[0],
          lastMessage: 'Is this from a smoke-free home?',
          timestamp: '1h ago',
          unread: false,
          messages: [
            { id: 'm1', sender: 'them', text: 'Hey, I am very interested. Is this from a smoke-free home?', timestamp: '9:00 AM' },
            { id: 'm2', sender: 'agent', text: 'Yes, it is! I keep all my listings in a climate-controlled, smoke-free environment.', timestamp: '9:15 AM' },
          ],
        });
      } else {
        // Seller 1: Competitive Business Seller
        mockConversations.push({
          id: `c-${itemId}-1`,
          username: 'outlet_direct',
          platform: selectedPlatforms[0],
          lastMessage: `I have several in stock. Can do $${(price * 1.05).toFixed(2)} shipped.`,
          timestamp: '5m ago',
          unread: true,
          messages: [
            { id: 'm1', sender: 'agent', text: `Hi! I am looking for this item. Do you have it in stock?`, timestamp: '11:00 AM' },
            { id: 'm2', sender: 'them', text: `I have several in stock. Can do $${(price * 1.05).toFixed(2)} shipped.`, timestamp: '11:05 AM' },
          ],
        });
        // Seller 2: "Too good to be true" seller
        mockConversations.push({
          id: `c-${itemId}-2`,
          username: 'quick_sale_user',
          platform: selectedPlatforms[1] || selectedPlatforms[0],
          lastMessage: 'I can do $1.00 if you buy today.',
          timestamp: '20m ago',
          unread: true,
          messages: [
            { id: 'm1', sender: 'agent', text: 'Hi, is the price flexible?', timestamp: '10:30 AM' },
            { id: 'm2', sender: 'them', text: 'I really need to get rid of this. I can do $1.00 if you buy today.', timestamp: '10:45 AM' },
          ],
        });
      }

      // 3. Create Local Item Object
      const newItem: Item = {
        id: itemId,
        type: listingType,
        name: name.trim(),
        description: description.trim(),
        condition,
        imageColor: '#8B5CF6',
        targetPrice: price,
        minPrice: minPrice ? parseFloat(minPrice) : undefined,
        maxPrice: maxPrice ? parseFloat(maxPrice) : undefined,
        autoAcceptThreshold: autoAcceptThreshold ? parseFloat(autoAcceptThreshold) : undefined,
        platforms: selectedPlatforms,
        status: aiActive ? 'active' : 'paused',
        quantity: parseInt(quantity) || 1,
        negotiationStyle,
        replyTone,
        initialPrice: initialPrice ? parseFloat(initialPrice) : undefined,
        photos: photos.length > 0 ? photos : ['https://via.placeholder.com/400'], // Use user photos if available
        marketData: mockMarketData,
        conversations: mockConversations,
      };

      // 4. Save to AsyncStorage
      await addLocalItem(newItem);

      emit('item:created');
      router.back();
    } catch (e: any) {
      Alert.alert('Error', e.message || 'Failed to create listing.');
    }
    setCreating(false);
  }

  return (
    <SafeAreaView
      style={[styles.container, { backgroundColor: colors.surface }]}
      edges={['top']}
    >
      {/* Nano Banana Processing Overlay */}
      <Modal visible={processingPhoto} transparent animationType="fade">
        <View style={overlayStyles.backdrop}>
          <View style={[overlayStyles.card, { backgroundColor: colors.surface }]}>
            <ActivityIndicator size="large" color={colors.accent} />
            <Text style={[overlayStyles.title, { color: colors.textPrimary }]}>
              Nano Banana ✨
            </Text>
            <Text style={[overlayStyles.step, { color: colors.textSecondary }]}>
              {processingStep || 'Processing...'}
            </Text>
            <Text style={[overlayStyles.hint, { color: colors.textMuted }]}>
              Gemini is creating a professional product photo with a white background
            </Text>
          </View>
        </View>
      </Modal>
      {/* Header */}
      <View style={[styles.header, { backgroundColor: colors.surface }]}>
        <TouchableOpacity
          onPress={() => router.back()}
          style={styles.backBtn}
          hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
        >
          <ArrowLeft size={20} color={colors.textPrimary} />
        </TouchableOpacity>
        <Text style={[styles.headerTitle, { color: colors.textPrimary }]}>
          New {listingType === 'buy' ? 'Buy' : 'Sell'} Listing
        </Text>
        <View style={{ width: 36 }} />
      </View>

      <KeyboardAvoidingView
        style={[{ flex: 1 }, { backgroundColor: colors.background }]}
        behavior={RNPlatform.OS === 'ios' ? 'padding' : undefined}
      >
        <ScrollView
          showsVerticalScrollIndicator={false}
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
        >

          {/* ── Photos ─────────────────────────────────────────────────────────── */}
          <SectionLabel label="Photos" colors={colors} />
          <View style={[styles.card, { backgroundColor: colors.surface }]}>
            {photos.length === 0 ? (
              <TouchableOpacity
                style={styles.emptyPhotos}
                onPress={handleAddPhoto}
                activeOpacity={0.7}
              >
                <Plus size={24} color={colors.textMuted} />
                <Text style={[styles.emptyPhotosText, { color: colors.textMuted }]}>
                  Add photos for your listing
                </Text>
                <Text style={[styles.emptyPhotosHint, { color: colors.textMuted }]}>
                  First photo will be the cover image
                </Text>
              </TouchableOpacity>
            ) : (
              <View style={styles.photoSection}>
                <ScrollView
                  horizontal
                  showsHorizontalScrollIndicator={false}
                  contentContainerStyle={styles.photoScroll}
                >
                  {photos.map((uri, idx) => (
                    <View key={`${uri}-${idx}`} style={styles.photoThumb}>
                      <Image source={{ uri }} style={styles.photoImage} resizeMode="cover" />
                      <TouchableOpacity
                        style={styles.photoDeleteBtn}
                        onPress={() => removePhoto(idx)}
                        hitSlop={{ top: 4, bottom: 4, left: 4, right: 4 }}
                      >
                        <X size={12} color="#FFF" />
                      </TouchableOpacity>
                      <View style={styles.photoBadge}>
                        <Text style={styles.photoBadgeText}>{idx + 1}</Text>
                      </View>
                    </View>
                  ))}
                </ScrollView>
                <TouchableOpacity
                  style={[styles.addMorePhotosBtn, { backgroundColor: colors.surfaceRaised }]}
                  onPress={handleAddPhoto}
                >
                  <Plus size={14} color={colors.textPrimary} />
                  <Text style={[styles.addMorePhotosText, { color: colors.textPrimary }]}>Add More</Text>
                </TouchableOpacity>
              </View>
            )}
          </View>

          {/* ── Basic Info ──────────────────────────────────────────────────────── */}
          <SectionLabel label="Basic Information" colors={colors} />
          <View style={[styles.card, { backgroundColor: colors.surface }]}>
            <InputField
              label="Listing Name *"
              value={name}
              onChangeText={setName}
              placeholder="e.g. Air Jordan 1 Retro High OG"
              colors={colors}
            />
            <Divider colors={colors} />
            <InputField
              label="Description"
              value={description}
              onChangeText={setDescription}
              placeholder="Describe the item, condition details, what's included..."
              multiline
              colors={colors}
            />
            <Divider colors={colors} />
            <View style={styles.fieldRow}>
              <Text style={[styles.fieldLabel, { color: colors.textPrimary }]}>Condition</Text>
              <View style={[styles.segmented, { backgroundColor: colors.muted }]}>
                {CONDITIONS.map(c => {
                  const active = condition === c;
                  return (
                    <TouchableOpacity
                      key={c}
                      style={[styles.segmentBtn, active && { backgroundColor: colors.surface }]}
                      onPress={() => setCondition(c)}
                    >
                      <Text style={[
                        styles.segmentText,
                        { color: active ? colors.textPrimary : colors.textMuted },
                        active && styles.segmentTextActive,
                      ]}>
                        {c}
                      </Text>
                    </TouchableOpacity>
                  );
                })}
              </View>
            </View>
            <Divider colors={colors} />
            <InputField
              label="Quantity"
              value={quantity}
              onChangeText={setQuantity}
              placeholder="1"
              keyboardType="number-pad"
              colors={colors}
            />
          </View>

          {/* ── Pricing ────────────────────────────────────────────────────────── */}
          <SectionLabel label="Pricing" colors={colors} />
          <View style={[styles.card, { backgroundColor: colors.surface }]}>
            <InputField
              label="Initial Price (optional)"
              value={initialPrice}
              onChangeText={setInitialPrice}
              placeholder="0"
              keyboardType="decimal-pad"
              prefix="$"
              hint="What you paid — enables profit tracking"
              colors={colors}
            />
            <Divider colors={colors} />
            <InputField
              label="Target Price *"
              value={targetPrice}
              onChangeText={setTargetPrice}
              placeholder="0"
              keyboardType="decimal-pad"
              prefix="$"
              colors={colors}
            />
            <Divider colors={colors} />
            <InputField
              label={listingType === 'sell' ? 'Min Acceptable' : 'Max Acceptable'}
              value={listingType === 'sell' ? minPrice : maxPrice}
              onChangeText={listingType === 'sell' ? setMinPrice : setMaxPrice}
              placeholder="0"
              keyboardType="decimal-pad"
              prefix="$"
              colors={colors}
            />
            <Divider colors={colors} />
            <InputField
              label={listingType === 'sell' ? 'Max Acceptable' : 'Min Acceptable'}
              value={listingType === 'sell' ? maxPrice : minPrice}
              onChangeText={listingType === 'sell' ? setMaxPrice : setMinPrice}
              placeholder="0"
              keyboardType="decimal-pad"
              prefix="$"
              colors={colors}
            />
            <Divider colors={colors} />
            <InputField
              label="Auto-Accept Threshold"
              value={autoAcceptThreshold}
              onChangeText={setAutoAcceptThreshold}
              placeholder="0"
              keyboardType="decimal-pad"
              prefix="$"
              colors={colors}
            />
          </View>

          {/* ── Platforms ──────────────────────────────────────────────────────── */}
          <SectionLabel label="Platforms" colors={colors} />
          <View style={[styles.card, { backgroundColor: colors.surface }]}>
            {ALL_PLATFORMS.map((p, idx) => {
              const selected = selectedPlatforms.includes(p);
              return (
                <React.Fragment key={p}>
                  {idx > 0 && <Divider colors={colors} />}
                  <TouchableOpacity
                    style={styles.platformRow}
                    onPress={() => togglePlatform(p)}
                    activeOpacity={0.7}
                  >
                    <Text style={[styles.platformName, { color: colors.textPrimary }]}>
                      {PLATFORM_NAMES[p]}
                    </Text>
                    <View style={[
                      styles.checkbox,
                      {
                        backgroundColor: selected ? colors.accent : 'transparent',
                        borderColor: selected ? colors.accent : colors.textMuted,
                      },
                    ]}>
                      {selected && <Check size={12} color="#FFF" strokeWidth={3} />}
                    </View>
                  </TouchableOpacity>
                </React.Fragment>
              );
            })}
          </View>

          {/* ── Agent Settings ─────────────────────────────────────────────────── */}
          <SectionLabel label="Agent Settings" colors={colors} />
          <View style={[styles.card, { backgroundColor: colors.surface }]}>
            <View style={styles.toggleRow}>
              <Text style={[styles.fieldLabel, { color: colors.textPrimary }]}>
                AI Agent Active
              </Text>
              <Switch
                value={aiActive}
                onValueChange={setAiActive}
                trackColor={{ true: colors.accent, false: colors.muted }}
                thumbColor={colors.white}
              />
            </View>
            <Divider colors={colors} />
            <View style={styles.fieldRow}>
              <Text style={[styles.fieldLabel, { color: colors.textPrimary }]}>Negotiation Style</Text>
              <View style={[styles.segmented, { backgroundColor: colors.muted }]}>
                {(['aggressive', 'moderate', 'passive'] as const).map(s => {
                  const active = negotiationStyle === s;
                  return (
                    <TouchableOpacity
                      key={s}
                      style={[styles.segmentBtn, active && { backgroundColor: colors.surface }]}
                      onPress={() => setNegotiationStyle(s)}
                    >
                      <Text style={[
                        styles.segmentText,
                        { color: active ? colors.textPrimary : colors.textMuted },
                        active && styles.segmentTextActive,
                      ]}>
                        {s.charAt(0).toUpperCase() + s.slice(1)}
                      </Text>
                    </TouchableOpacity>
                  );
                })}
              </View>
            </View>
            <Divider colors={colors} />
            <View style={styles.fieldRow}>
              <Text style={[styles.fieldLabel, { color: colors.textPrimary }]}>Reply Tone</Text>
              <View style={[styles.segmented, { backgroundColor: colors.muted }]}>
                {(['professional', 'casual', 'firm'] as const).map(t => {
                  const active = replyTone === t;
                  return (
                    <TouchableOpacity
                      key={t}
                      style={[styles.segmentBtn, active && { backgroundColor: colors.surface }]}
                      onPress={() => setReplyTone(t)}
                    >
                      <Text style={[
                        styles.segmentText,
                        { color: active ? colors.textPrimary : colors.textMuted },
                        active && styles.segmentTextActive,
                      ]}>
                        {t.charAt(0).toUpperCase() + t.slice(1)}
                      </Text>
                    </TouchableOpacity>
                  );
                })}
              </View>
            </View>
          </View>

          {/* Create button */}
          <TouchableOpacity
            style={[styles.createBtn, { backgroundColor: colors.accent, opacity: creating ? 0.7 : 1 }]}
            onPress={handleCreate}
            activeOpacity={0.7}
            disabled={creating}
          >
            {creating ? (
              <ActivityIndicator color="#FFFFFF" size="small" />
            ) : (
              <Text style={styles.createBtnText}>Create Listing</Text>
            )}
          </TouchableOpacity>

          <View style={{ height: 32 }} />
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

// ─── Reusable sub-components ──────────────────────────────────────────────────

function SectionLabel({ label, colors }: { label: string; colors: any }) {
  return (
    <Text style={[styles.sectionLabel, { color: colors.textMuted }]}>
      {label.toUpperCase()}
    </Text>
  );
}

function Divider({ colors }: { colors: any }) {
  return <View style={[styles.divider, { backgroundColor: colors.divider }]} />;
}

function InputField({
  label, value, onChangeText, placeholder, multiline, keyboardType, prefix, hint, colors,
}: {
  label: string;
  value: string;
  onChangeText: (v: string) => void;
  placeholder: string;
  multiline?: boolean;
  keyboardType?: 'default' | 'number-pad' | 'decimal-pad';
  prefix?: string;
  hint?: string;
  colors: any;
}) {
  return (
    <View style={[styles.inputField, multiline && styles.inputFieldMultiline]}>
      <Text style={[styles.fieldLabel, { color: colors.textPrimary }]}>{label}</Text>
      <View style={styles.inputRow}>
        {prefix && (
          <Text style={[styles.inputPrefix, { color: colors.textMuted }]}>{prefix}</Text>
        )}
        <TextInput
          style={[
            styles.textInput,
            { color: colors.textPrimary },
            multiline && styles.textInputMultiline,
          ]}
          value={value}
          onChangeText={onChangeText}
          placeholder={placeholder}
          placeholderTextColor={colors.textMuted}
          multiline={multiline}
          keyboardType={keyboardType}
          returnKeyType={multiline ? 'default' : 'done'}
        />
      </View>
      {hint && <Text style={[styles.fieldHint, { color: colors.textMuted }]}>{hint}</Text>}
    </View>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

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
  createBtn: {
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: 'center',
    marginTop: 32,
  },
  createBtnText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#FFFFFF',
  },

  scrollContent: {
    paddingHorizontal: 16,
    paddingTop: 8,
  },

  sectionLabel: {
    fontSize: 11,
    fontWeight: '600',
    letterSpacing: 0.8,
    marginTop: 24,
    marginBottom: 8,
    paddingHorizontal: 4,
  },

  card: {
    borderRadius: 12,
    overflow: 'hidden',
  },
  divider: { height: 1 },

  // Photos
  emptyPhotos: {
    paddingVertical: 32,
    alignItems: 'center',
    gap: 8,
  },
  emptyPhotosText: {
    fontSize: 14,
    fontWeight: '500',
  },
  emptyPhotosHint: {
    fontSize: 12,
    textAlign: 'center',
  },
  photoSection: {
    padding: 12,
    gap: 10,
  },
  photoScroll: {
    gap: 8,
  },
  photoThumb: {
    width: 80,
    height: 80,
    borderRadius: 8,
    overflow: 'hidden',
    position: 'relative',
  },
  photoImage: {
    width: 80,
    height: 80,
  },
  photoDeleteBtn: {
    position: 'absolute',
    top: 4,
    right: 4,
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: 'rgba(0,0,0,0.6)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  photoBadge: {
    position: 'absolute',
    bottom: 4,
    left: 4,
    backgroundColor: 'rgba(0,0,0,0.6)',
    borderRadius: 4,
    paddingHorizontal: 5,
    paddingVertical: 1,
  },
  photoBadgeText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#FFF',
  },
  addMorePhotosBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    borderRadius: 8,
    paddingVertical: 10,
  },
  addMorePhotosText: {
    fontSize: 13,
    fontWeight: '600',
  },

  // Form fields
  inputField: {
    paddingHorizontal: 14,
    paddingVertical: 12,
    gap: 6,
  },
  inputFieldMultiline: {
    paddingBottom: 14,
  },
  fieldLabel: {
    fontSize: 14,
    fontWeight: '500',
  },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
  },
  inputPrefix: {
    fontSize: 16,
    fontWeight: '600',
  },
  textInput: {
    fontSize: 16,
    flex: 1,
    paddingVertical: 0,
  },
  fieldHint: {
    fontSize: 12,
    marginTop: 4,
  },
  textInputMultiline: {
    minHeight: 60,
    textAlignVertical: 'top',
  },

  // Segmented controls
  fieldRow: {
    paddingHorizontal: 14,
    paddingVertical: 12,
    gap: 10,
  },
  segmented: {
    flexDirection: 'row',
    borderRadius: 8,
    padding: 2,
    gap: 2,
  },
  segmentBtn: {
    flex: 1,
    alignItems: 'center',
    paddingVertical: 7,
    borderRadius: 6,
  },
  segmentText: {
    fontSize: 12,
    fontWeight: '500',
  },
  segmentTextActive: {
    fontWeight: '700',
  },

  // Toggle row
  toggleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 14,
    paddingVertical: 12,
  },

  // Platforms
  platformRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 14,
    paddingVertical: 13,
  },
  platformName: {
    fontSize: 15,
    fontWeight: '500',
  },
  checkbox: {
    width: 22,
    height: 22,
    borderRadius: 6,
    borderWidth: 1.5,
    alignItems: 'center',
    justifyContent: 'center',
  },
});

const overlayStyles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.65)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  card: {
    width: '100%',
    borderRadius: 20,
    padding: 32,
    alignItems: 'center',
    gap: 12,
  },
  title: {
    fontSize: 22,
    fontWeight: '800',
    letterSpacing: -0.5,
    marginTop: 8,
  },
  step: {
    fontSize: 14,
    fontWeight: '500',
    textAlign: 'center',
  },
  hint: {
    fontSize: 12,
    textAlign: 'center',
    lineHeight: 18,
    paddingHorizontal: 8,
  },
});
