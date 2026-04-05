import React, { useState, useEffect } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity,
  TextInput, Alert, Image, KeyboardAvoidingView, Platform as RNPlatform,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, router } from 'expo-router';
import {
  ArrowLeft, Plus, X, Check, Camera, Sparkles, Edit3,
} from 'lucide-react-native';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import { supabase } from '../lib/supabase';
import { pickImage } from '../lib/imagePicker';
import { emit } from '../lib/events';
import { Platform, PLATFORM_NAMES, NegotiationStyle, ReplyTone } from '../data/mockData';
import { API_BASE_URL } from '../constants/config';

const ALL_PLATFORMS: Platform[] = ['ebay', 'depop', 'mercari', 'offerup', 'facebook'];
const CONDITIONS = ['New', 'Like New', 'Good', 'Fair', 'Poor'];
const RESPONSE_DELAYS = ['1 min', '5 min', '15 min', '30 min'];

type EntryMethod = 'manual' | 'ai';

export default function NewListingScreen() {
  const { type } = useLocalSearchParams<{ type: string }>();
  const { colors } = useTheme();
  const { user, accessToken } = useAuth();
  const listingType = type === 'buy' ? 'buy' : 'sell';

  // ─── Entry Method ───────────────────────────────────────────────────────────
  const [method, setMethod] = useState<EntryMethod>('ai');

  // ─── Form State ─────────────────────────────────────────────────────────────
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [condition, setCondition] = useState('Good');
  const [quantity, setQuantity] = useState('1');
  const [initialPrice, setInitialPrice] = useState('');
  const [autoAcceptThreshold, setAutoAcceptThreshold] = useState('');
  const [selectedPlatforms, setSelectedPlatforms] = useState<Platform[]>([]);
  const [negotiationStyle, setNegotiationStyle] = useState<NegotiationStyle>('moderate');
  const [replyTone, setReplyTone] = useState<ReplyTone>('professional');
  const [responseDelay, setResponseDelay] = useState('5 min');
  const [photos, setPhotos] = useState<string[]>([]);

  // ─── AI Flow State ──────────────────────────────────────────────────────────
  const [aiAnalyzing, setAiAnalyzing] = useState(false);
  const [aiDone, setAiDone] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);
  const [aiGeneratedPhotos, setAiGeneratedPhotos] = useState<string[]>([]);

  // ─── Save State ─────────────────────────────────────────────────────────────
  const [saving, setSaving] = useState(false);
  const [settingsLoaded, setSettingsLoaded] = useState(false);

  // ─── Load user_settings defaults on mount ───────────────────────────────────
  useEffect(() => {
    if (!user) return;
    (async () => {
      const { data } = await supabase
        .from('user_settings')
        .select('*')
        .eq('user_id', user.id)
        .single();
      if (data) {
        setNegotiationStyle(data.negotiation_style);
        setReplyTone(data.reply_tone);
        setResponseDelay(data.response_delay);
      }
      setSettingsLoaded(true);
    })();
  }, [user]);

  // ─── Helpers ────────────────────────────────────────────────────────────────

  function togglePlatform(p: Platform) {
    setSelectedPlatforms(prev =>
      prev.includes(p) ? prev.filter(x => x !== p) : [...prev, p]
    );
  }

  async function handleAddPhoto() {
    const uris = await pickImage({ shape: 'rectangle', multiple: false });
    if (uris.length > 0) {
      setPhotos(prev => [...prev, ...uris]);
    }
  }

  function removePhoto(idx: number) {
    setPhotos(prev => prev.filter((_, i) => i !== idx));
  }

  function removeAiPhoto(idx: number) {
    setAiGeneratedPhotos(prev => prev.filter((_, i) => i !== idx));
  }

  // ─── Upload a single photo to Supabase Storage ─────────────────────────────

  async function uploadSinglePhoto(
    uri: string,
    itemId: string,
    index: number,
  ): Promise<string | null> {
    if (!user) return null;

    const ext = uri.split('.').pop()?.toLowerCase() || 'jpg';
    const fileName = `${Date.now()}_${index}.${ext}`;
    const path = `${user.id}/${itemId}/${fileName}`;

    const formData = new FormData();
    formData.append('', {
      uri,
      name: fileName,
      type: `image/${ext === 'jpg' ? 'jpeg' : ext}`,
    } as any);

    const { error: uploadError } = await supabase.storage
      .from('item-photos')
      .upload(path, formData, { contentType: 'multipart/form-data' });

    if (uploadError) return null;

    const { data: urlData } = supabase.storage.from('item-photos').getPublicUrl(path);
    return urlData.publicUrl;
  }

  // ─── Upload all photos and insert into item_photos ──────────────────────────

  async function uploadAndInsertPhotos(itemId: string): Promise<void> {
    if (!user) return;

    // Combine manually added photos and AI-generated photo URLs
    const allLocalPhotos = [...photos]; // local URIs that need uploading
    const allRemoteUrls = [...aiGeneratedPhotos]; // already remote URLs

    let sortOrder = 0;

    // Upload local photos
    for (const uri of allLocalPhotos) {
      const publicUrl = await uploadSinglePhoto(uri, itemId, sortOrder);
      if (publicUrl) {
        await supabase.from('item_photos').insert({
          item_id: itemId,
          photo_url: publicUrl,
          sort_order: sortOrder,
        });
      }
      sortOrder++;
    }

    // Insert AI-generated photos (already have URLs)
    for (const url of allRemoteUrls) {
      await supabase.from('item_photos').insert({
        item_id: itemId,
        photo_url: url,
        sort_order: sortOrder,
      });
      sortOrder++;
    }
  }

  // ─── AI Analyze ─────────────────────────────────────────────────────────────

  async function handleAnalyze() {
    if (photos.length === 0) {
      Alert.alert('No Photo', 'Please add at least one photo to analyze.');
      return;
    }
    if (selectedPlatforms.length === 0) {
      Alert.alert('No Platforms', 'Please select at least one platform before analyzing.');
      return;
    }
    if (!user || !accessToken) return;

    setAiAnalyzing(true);
    setAiError(null);
    setAiDone(false);

    try {
      // 1. Create a temporary draft item to get an ID for photo storage
      const { data: draftItem, error: draftError } = await supabase
        .from('items')
        .insert({
          user_id: user.id,
          type: listingType,
          name: 'Analyzing...',
          status: 'draft',
          condition: 'Good',
          negotiation_style: negotiationStyle,
          reply_tone: replyTone,
          response_delay: responseDelay,
          quantity: parseInt(quantity) || 1,
          image_color: '#6EE7B7',
        })
        .select()
        .single();

      if (draftError) throw draftError;
      const draftId = draftItem.id;

      // 2. Upload the first photo to Supabase storage to get a public URL
      const photoUrl = await uploadSinglePhoto(photos[0], draftId, 0);
      if (!photoUrl) {
        // Clean up draft
        await supabase.from('items').delete().eq('id', draftId);
        throw new Error('Failed to upload photo for analysis.');
      }

      // 3. Call the AI analysis endpoint
      const generatePhotos = listingType === 'sell';
      const response = await fetch(`${API_BASE_URL}/ai/analyze-item`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          photo_url: photoUrl,
          item_id: draftId,
          generate_photos: generatePhotos,
          photo_count: 4,
        }),
      });

      if (!response.ok) {
        const errBody = await response.text().catch(() => '');
        // Clean up draft
        await supabase.from('items').delete().eq('id', draftId);
        throw new Error(`Analysis failed (${response.status}): ${errBody}`);
      }

      const result = await response.json();

      // 4. Pre-fill fields from AI response
      if (result.name) setName(result.name);
      if (result.description) setDescription(result.description);
      if (result.condition) setCondition(result.condition);
      if (result.generated_photo_urls && Array.isArray(result.generated_photo_urls)) {
        setAiGeneratedPhotos(result.generated_photo_urls);
      }

      // 5. Clean up the temporary draft (we will create the real item on save)
      await supabase.from('items').delete().eq('id', draftId);

      setAiDone(true);
    } catch (e: any) {
      setAiError(e.message || 'Analysis failed. You can fill in the details manually.');
    } finally {
      setAiAnalyzing(false);
    }
  }

  // ─── Validation ─────────────────────────────────────────────────────────────

  function validate(): boolean {
    if (!name.trim()) {
      Alert.alert('Missing Name', 'Please enter a name for your listing.');
      return false;
    }
    if (!description.trim()) {
      Alert.alert('Missing Description', 'Please enter a description.');
      return false;
    }
    if (selectedPlatforms.length === 0) {
      Alert.alert('No Platforms', 'Please select at least one platform.');
      return false;
    }

    const totalPhotos = photos.length + aiGeneratedPhotos.length;
    const requiredPhotos = listingType === 'sell' ? 4 : 1;
    if (totalPhotos < requiredPhotos) {
      Alert.alert(
        'Not Enough Photos',
        `${listingType === 'sell' ? 'Sell' : 'Buy'} listings require at least ${requiredPhotos} photo${requiredPhotos > 1 ? 's' : ''}.`
      );
      return false;
    }
    return true;
  }

  // ─── Save ───────────────────────────────────────────────────────────────────

  async function handleSave() {
    if (!validate()) return;
    if (!user) return;

    setSaving(true);

    try {
      // 1. Insert item
      const { data: item, error: itemError } = await supabase
        .from('items')
        .insert({
          user_id: user.id,
          type: listingType,
          name: name.trim(),
          description: description.trim(),
          condition,
          quantity: parseInt(quantity) || 1,
          initial_price: initialPrice ? parseFloat(initialPrice) : null,
          auto_accept_threshold: autoAcceptThreshold ? parseFloat(autoAcceptThreshold) : null,
          negotiation_style: negotiationStyle,
          reply_tone: replyTone,
          response_delay: responseDelay,
          status: 'paused',
          image_color: '#6EE7B7',
        })
        .select()
        .single();

      if (itemError) throw itemError;
      const itemId = item.id;

      // 2. Insert platforms
      await supabase
        .from('item_platforms')
        .insert(selectedPlatforms.map(p => ({ item_id: itemId, platform: p })));

      // 3. Upload photos and insert into item_photos
      await uploadAndInsertPhotos(itemId);

      // 4. Emit event and navigate
      emit('item:created');
      router.replace('/');
    } catch (e: any) {
      Alert.alert('Error', e.message || 'Failed to save listing.');
    } finally {
      setSaving(false);
    }
  }

  // ─── Render: Method Toggle ──────────────────────────────────────────────────

  function renderMethodToggle() {
    return (
      <View style={[toggleStyles.container, { backgroundColor: colors.muted }]}>
        <TouchableOpacity
          style={[
            toggleStyles.tab,
            method === 'manual' && { backgroundColor: colors.surface },
          ]}
          onPress={() => setMethod('manual')}
          activeOpacity={0.7}
        >
          <Edit3
            size={16}
            color={method === 'manual' ? colors.textPrimary : colors.textMuted}
          />
          <Text
            style={[
              toggleStyles.tabText,
              { color: method === 'manual' ? colors.textPrimary : colors.textMuted },
              method === 'manual' && toggleStyles.tabTextActive,
            ]}
          >
            Manual
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[
            toggleStyles.tab,
            method === 'ai' && { backgroundColor: colors.surface },
          ]}
          onPress={() => setMethod('ai')}
          activeOpacity={0.7}
        >
          <Sparkles
            size={16}
            color={method === 'ai' ? colors.accent : colors.textMuted}
          />
          <Text
            style={[
              toggleStyles.tabText,
              { color: method === 'ai' ? colors.accent : colors.textMuted },
              method === 'ai' && toggleStyles.tabTextActive,
            ]}
          >
            AI Auto-fill
          </Text>
        </TouchableOpacity>
      </View>
    );
  }

  // ─── Render: Photo Grid ─────────────────────────────────────────────────────

  function renderPhotos(label: string, requiredCount: number) {
    const totalPhotos = photos.length + aiGeneratedPhotos.length;
    return (
      <>
        <SectionLabel
          label={`${label} (${totalPhotos}/${requiredCount} required)`}
          colors={colors}
          required
        />
        <View style={[styles.card, { backgroundColor: colors.surface }]}>
          {totalPhotos === 0 ? (
            <TouchableOpacity
              style={styles.emptyPhotos}
              onPress={handleAddPhoto}
              activeOpacity={0.7}
            >
              <Camera size={28} color={colors.textMuted} />
              <Text style={[styles.emptyPhotosText, { color: colors.textMuted }]}>
                Tap to add photos
              </Text>
              <Text style={[styles.emptyPhotosHint, { color: colors.textMuted }]}>
                {listingType === 'sell'
                  ? '4 photos required for sell listings'
                  : '1 photo required for buy listings'}
              </Text>
            </TouchableOpacity>
          ) : (
            <View style={styles.photoSection}>
              <ScrollView
                horizontal
                showsHorizontalScrollIndicator={false}
                contentContainerStyle={styles.photoScroll}
              >
                {/* Manually added local photos */}
                {photos.map((uri, idx) => (
                  <View key={`local-${idx}`} style={styles.photoThumb}>
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
                {/* AI-generated photos */}
                {aiGeneratedPhotos.map((url, idx) => (
                  <View key={`ai-${idx}`} style={styles.photoThumb}>
                    <Image source={{ uri: url }} style={styles.photoImage} resizeMode="cover" />
                    <TouchableOpacity
                      style={styles.photoDeleteBtn}
                      onPress={() => removeAiPhoto(idx)}
                      hitSlop={{ top: 4, bottom: 4, left: 4, right: 4 }}
                    >
                      <X size={12} color="#FFF" />
                    </TouchableOpacity>
                    <View style={[styles.photoBadge, { backgroundColor: 'rgba(34,197,94,0.8)' }]}>
                      <Text style={styles.photoBadgeText}>AI</Text>
                    </View>
                  </View>
                ))}
              </ScrollView>
              <TouchableOpacity
                style={[styles.addMorePhotosBtn, { backgroundColor: colors.surfaceRaised }]}
                onPress={handleAddPhoto}
              >
                <Plus size={14} color={colors.textPrimary} />
                <Text style={[styles.addMorePhotosText, { color: colors.textPrimary }]}>
                  Add More
                </Text>
              </TouchableOpacity>
            </View>
          )}
        </View>
      </>
    );
  }

  // ─── Render: Basic Info Section ─────────────────────────────────────────────

  function renderBasicInfo() {
    return (
      <>
        <SectionLabel label="Basic Information" colors={colors} />
        <View style={[styles.card, { backgroundColor: colors.surface }]}>
          <InputField
            label="Name"
            value={name}
            onChangeText={setName}
            placeholder="e.g. Air Jordan 1 Retro High OG"
            colors={colors}
            required
          />
          <Divider colors={colors} />
          <InputField
            label="Description"
            value={description}
            onChangeText={setDescription}
            placeholder="Describe the item, condition details, what's included..."
            multiline
            colors={colors}
            required
          />
          <Divider colors={colors} />
          <View style={styles.fieldRow}>
            <Text style={[styles.fieldLabel, { color: colors.textPrimary }]}>
              Condition <Text style={[styles.requiredAsterisk, { color: colors.accent }]}>*</Text>
            </Text>
            <View style={[styles.segmented, { backgroundColor: colors.muted }]}>
              {CONDITIONS.map(c => {
                const active = condition === c;
                return (
                  <TouchableOpacity
                    key={c}
                    style={[styles.segmentBtn, active && { backgroundColor: colors.surface }]}
                    onPress={() => setCondition(c)}
                  >
                    <Text
                      style={[
                        styles.segmentText,
                        { color: active ? colors.textPrimary : colors.textMuted },
                        active && styles.segmentTextActive,
                      ]}
                    >
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
            required
          />
        </View>
      </>
    );
  }

  // ─── Render: Pricing Section ────────────────────────────────────────────────

  function renderPricing() {
    return (
      <>
        <SectionLabel label="Pricing (Optional)" colors={colors} />
        <View style={[styles.card, { backgroundColor: colors.surface }]}>
          <InputField
            label="Initial Price"
            value={initialPrice}
            onChangeText={setInitialPrice}
            placeholder="0.00"
            keyboardType="decimal-pad"
            prefix="$"
            hint="What you paid -- enables profit tracking"
            colors={colors}
          />
          <Divider colors={colors} />
          <InputField
            label="Auto-Accept Threshold"
            value={autoAcceptThreshold}
            onChangeText={setAutoAcceptThreshold}
            placeholder="0.00"
            keyboardType="decimal-pad"
            prefix="$"
            hint="Automatically accept offers at or above this price"
            colors={colors}
          />
        </View>
      </>
    );
  }

  // ─── Render: Platforms Section ──────────────────────────────────────────────

  function renderPlatforms() {
    return (
      <>
        <SectionLabel label="Platforms" colors={colors} required />
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
                  <View
                    style={[
                      styles.checkbox,
                      {
                        backgroundColor: selected ? colors.accent : 'transparent',
                        borderColor: selected ? colors.accent : colors.textMuted,
                      },
                    ]}
                  >
                    {selected && <Check size={12} color="#FFF" strokeWidth={3} />}
                  </View>
                </TouchableOpacity>
              </React.Fragment>
            );
          })}
        </View>
      </>
    );
  }

  // ─── Render: Agent Settings Section ─────────────────────────────────────────

  function renderAgentSettings() {
    return (
      <>
        <SectionLabel label="Agent Settings" colors={colors} />
        <View style={[styles.card, { backgroundColor: colors.surface }]}>
          {/* Negotiation Style */}
          <View style={styles.fieldRow}>
            <Text style={[styles.fieldLabel, { color: colors.textPrimary }]}>
              Negotiation Style <Text style={[styles.requiredAsterisk, { color: colors.accent }]}>*</Text>
            </Text>
            <View style={[styles.segmented, { backgroundColor: colors.muted }]}>
              {(['aggressive', 'moderate', 'passive'] as const).map(s => {
                const active = negotiationStyle === s;
                return (
                  <TouchableOpacity
                    key={s}
                    style={[styles.segmentBtn, active && { backgroundColor: colors.surface }]}
                    onPress={() => setNegotiationStyle(s)}
                  >
                    <Text
                      style={[
                        styles.segmentText,
                        { color: active ? colors.textPrimary : colors.textMuted },
                        active && styles.segmentTextActive,
                      ]}
                    >
                      {s.charAt(0).toUpperCase() + s.slice(1)}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </View>
          </View>

          <Divider colors={colors} />

          {/* Reply Tone */}
          <View style={styles.fieldRow}>
            <Text style={[styles.fieldLabel, { color: colors.textPrimary }]}>
              Reply Tone <Text style={[styles.requiredAsterisk, { color: colors.accent }]}>*</Text>
            </Text>
            <View style={[styles.segmented, { backgroundColor: colors.muted }]}>
              {(['professional', 'casual', 'firm'] as const).map(t => {
                const active = replyTone === t;
                return (
                  <TouchableOpacity
                    key={t}
                    style={[styles.segmentBtn, active && { backgroundColor: colors.surface }]}
                    onPress={() => setReplyTone(t)}
                  >
                    <Text
                      style={[
                        styles.segmentText,
                        { color: active ? colors.textPrimary : colors.textMuted },
                        active && styles.segmentTextActive,
                      ]}
                    >
                      {t.charAt(0).toUpperCase() + t.slice(1)}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </View>
          </View>

          <Divider colors={colors} />

          {/* Response Delay */}
          <View style={styles.fieldRow}>
            <Text style={[styles.fieldLabel, { color: colors.textPrimary }]}>
              Response Delay <Text style={[styles.requiredAsterisk, { color: colors.accent }]}>*</Text>
            </Text>
            <View style={[styles.segmented, { backgroundColor: colors.muted }]}>
              {RESPONSE_DELAYS.map(d => {
                const active = responseDelay === d;
                return (
                  <TouchableOpacity
                    key={d}
                    style={[styles.segmentBtn, active && { backgroundColor: colors.surface }]}
                    onPress={() => setResponseDelay(d)}
                  >
                    <Text
                      style={[
                        styles.segmentText,
                        { color: active ? colors.textPrimary : colors.textMuted },
                        active && styles.segmentTextActive,
                      ]}
                    >
                      {d}
                    </Text>
                  </TouchableOpacity>
                );
              })}
            </View>
          </View>
        </View>
      </>
    );
  }

  // ─── Render: AI Pre-fill Step (before analysis) ─────────────────────────────

  function renderAiPreStep() {
    return (
      <>
        {/* Platforms and Quantity needed before AI runs */}
        <SectionLabel label="Setup (Required Before AI)" colors={colors} />
        <View style={[styles.card, { backgroundColor: colors.surface }]}>
          <InputField
            label="Quantity"
            value={quantity}
            onChangeText={setQuantity}
            placeholder="1"
            keyboardType="number-pad"
            colors={colors}
            required
          />
        </View>

        {renderPlatforms()}

        {/* Photo upload for AI */}
        <SectionLabel label="Photo for Analysis" colors={colors} required />
        <View style={[styles.card, { backgroundColor: colors.surface }]}>
          {photos.length === 0 ? (
            <TouchableOpacity
              style={styles.emptyPhotos}
              onPress={handleAddPhoto}
              activeOpacity={0.7}
            >
              <Camera size={28} color={colors.textMuted} />
              <Text style={[styles.emptyPhotosText, { color: colors.textMuted }]}>
                Upload 1 photo for AI analysis
              </Text>
              <Text style={[styles.emptyPhotosHint, { color: colors.textMuted }]}>
                The AI will identify and describe your item
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
                  <View key={`local-${idx}`} style={styles.photoThumb}>
                    <Image source={{ uri }} style={styles.photoImage} resizeMode="cover" />
                    <TouchableOpacity
                      style={styles.photoDeleteBtn}
                      onPress={() => removePhoto(idx)}
                      hitSlop={{ top: 4, bottom: 4, left: 4, right: 4 }}
                    >
                      <X size={12} color="#FFF" />
                    </TouchableOpacity>
                  </View>
                ))}
              </ScrollView>
              {photos.length < 1 && (
                <TouchableOpacity
                  style={[styles.addMorePhotosBtn, { backgroundColor: colors.surfaceRaised }]}
                  onPress={handleAddPhoto}
                >
                  <Plus size={14} color={colors.textPrimary} />
                  <Text style={[styles.addMorePhotosText, { color: colors.textPrimary }]}>
                    Add Photo
                  </Text>
                </TouchableOpacity>
              )}
            </View>
          )}
        </View>

        {/* Analyze Button */}
        <TouchableOpacity
          style={[
            styles.analyzeBtn,
            {
              backgroundColor:
                photos.length > 0 && selectedPlatforms.length > 0
                  ? colors.accent
                  : colors.muted,
              marginTop: 28,
            },
          ]}
          onPress={handleAnalyze}
          activeOpacity={0.7}
          disabled={photos.length === 0 || selectedPlatforms.length === 0 || aiAnalyzing}
        >
          {aiAnalyzing ? (
            <View style={styles.analyzingRow}>
              <ActivityIndicator color="#FFFFFF" size="small" />
              <Text style={styles.analyzeBtnText}>Analyzing...</Text>
            </View>
          ) : (
            <View style={styles.analyzingRow}>
              <Sparkles size={18} color="#FFF" />
              <Text style={styles.analyzeBtnText}>Analyze with AI</Text>
            </View>
          )}
        </TouchableOpacity>

        {/* Error */}
        {aiError && (
          <View style={[styles.errorBanner, { backgroundColor: colors.destructive + '15' }]}>
            <Text style={[styles.errorText, { color: colors.destructive }]}>{aiError}</Text>
            <Text style={[styles.errorHint, { color: colors.textMuted }]}>
              You can try again or switch to Manual mode.
            </Text>
          </View>
        )}
      </>
    );
  }

  // ─── Render: AI Review Step (after analysis) ────────────────────────────────

  function renderAiReviewForm() {
    const requiredPhotos = listingType === 'sell' ? 4 : 1;
    return (
      <>
        {/* Success banner */}
        <View style={[styles.successBanner, { backgroundColor: colors.accent + '15' }]}>
          <Sparkles size={16} color={colors.accent} />
          <View style={{ flex: 1 }}>
            <Text style={[styles.successTitle, { color: colors.accent }]}>
              AI Analysis Complete
            </Text>
            <Text style={[styles.successHint, { color: colors.textMuted }]}>
              Review and edit the auto-filled fields below.
            </Text>
          </View>
        </View>

        {renderPhotos('Photos', requiredPhotos)}
        {renderBasicInfo()}
        {renderPricing()}
        {renderPlatforms()}
        {renderAgentSettings()}

        {/* Save Button */}
        <TouchableOpacity
          style={[
            styles.createBtn,
            { backgroundColor: colors.accent, opacity: saving ? 0.7 : 1, marginTop: 32 },
          ]}
          onPress={handleSave}
          activeOpacity={0.7}
          disabled={saving}
        >
          {saving ? (
            <ActivityIndicator color="#FFFFFF" size="small" />
          ) : (
            <Text style={styles.createBtnText}>Save Listing</Text>
          )}
        </TouchableOpacity>

        <View style={{ height: 40 }} />
      </>
    );
  }

  // ─── Render: Manual Full Form ───────────────────────────────────────────────

  function renderManualForm() {
    const requiredPhotos = listingType === 'sell' ? 4 : 1;
    return (
      <>
        {renderPhotos('Photos', requiredPhotos)}
        {renderBasicInfo()}
        {renderPricing()}
        {renderPlatforms()}
        {renderAgentSettings()}

        {/* Save Button */}
        <TouchableOpacity
          style={[
            styles.createBtn,
            { backgroundColor: colors.accent, opacity: saving ? 0.7 : 1, marginTop: 32 },
          ]}
          onPress={handleSave}
          activeOpacity={0.7}
          disabled={saving}
        >
          {saving ? (
            <ActivityIndicator color="#FFFFFF" size="small" />
          ) : (
            <Text style={styles.createBtnText}>Save Listing</Text>
          )}
        </TouchableOpacity>

        <View style={{ height: 40 }} />
      </>
    );
  }

  // ─── Render: AI Flow Content ────────────────────────────────────────────────

  function renderAiContent() {
    if (aiAnalyzing) {
      return (
        <View style={styles.analyzingContainer}>
          <View style={[styles.analyzingCard, { backgroundColor: colors.surface }]}>
            <View style={[styles.spinnerCircle, { backgroundColor: colors.accent + '20' }]}>
              <ActivityIndicator color={colors.accent} size="large" />
            </View>
            <Text style={[styles.analyzingTitle, { color: colors.textPrimary }]}>
              Analyzing Your Item
            </Text>
            <Text style={[styles.analyzingSubtitle, { color: colors.textMuted }]}>
              {listingType === 'sell'
                ? 'Identifying item and generating listing photos...'
                : 'Identifying item details...'}
            </Text>
          </View>
        </View>
      );
    }

    if (aiDone) {
      return renderAiReviewForm();
    }

    return renderAiPreStep();
  }

  // ─── Main Render ────────────────────────────────────────────────────────────

  if (!settingsLoaded) {
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
          <Text style={[styles.headerTitle, { color: colors.textPrimary }]}>
            New {listingType === 'buy' ? 'Buy' : 'Sell'} Listing
          </Text>
          <View style={{ width: 36 }} />
        </View>
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: colors.background }}>
          <ActivityIndicator color={colors.textMuted} />
        </View>
      </SafeAreaView>
    );
  }

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
          {/* Method Toggle */}
          {renderMethodToggle()}

          {/* Content */}
          {method === 'manual' ? renderManualForm() : renderAiContent()}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

// ─── Reusable sub-components ────────────────────────────────────────────────

function SectionLabel({
  label,
  colors,
  required,
}: {
  label: string;
  colors: any;
  required?: boolean;
}) {
  return (
    <Text style={[styles.sectionLabel, { color: colors.textMuted }]}>
      {label.toUpperCase()}
      {required && (
        <Text style={{ color: colors.accent }}> *</Text>
      )}
    </Text>
  );
}

function Divider({ colors }: { colors: any }) {
  return <View style={[styles.divider, { backgroundColor: colors.divider }]} />;
}

function InputField({
  label,
  value,
  onChangeText,
  placeholder,
  multiline,
  keyboardType,
  prefix,
  hint,
  colors,
  required,
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
  required?: boolean;
}) {
  return (
    <View style={[styles.inputField, multiline && styles.inputFieldMultiline]}>
      <Text style={[styles.fieldLabel, { color: colors.textPrimary }]}>
        {label}
        {required && (
          <Text style={[styles.requiredAsterisk, { color: colors.accent }]}> *</Text>
        )}
      </Text>
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

// ─── Styles ─────────────────────────────────────────────────────────────────

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
  requiredAsterisk: {
    fontSize: 14,
    fontWeight: '700',
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

  // Buttons
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
  analyzeBtn: {
    borderRadius: 12,
    paddingVertical: 16,
    alignItems: 'center',
  },
  analyzeBtnText: {
    fontSize: 16,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  analyzingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },

  // Analyzing state
  analyzingContainer: {
    paddingTop: 40,
    alignItems: 'center',
  },
  analyzingCard: {
    borderRadius: 16,
    padding: 32,
    alignItems: 'center',
    width: '100%',
    gap: 16,
  },
  spinnerCircle: {
    width: 72,
    height: 72,
    borderRadius: 36,
    alignItems: 'center',
    justifyContent: 'center',
  },
  analyzingTitle: {
    fontSize: 18,
    fontWeight: '700',
  },
  analyzingSubtitle: {
    fontSize: 14,
    textAlign: 'center',
    lineHeight: 20,
  },

  // Banners
  errorBanner: {
    borderRadius: 10,
    padding: 14,
    marginTop: 16,
    gap: 4,
  },
  errorText: {
    fontSize: 14,
    fontWeight: '600',
  },
  errorHint: {
    fontSize: 13,
  },
  successBanner: {
    flexDirection: 'row',
    gap: 12,
    borderRadius: 10,
    padding: 14,
    marginTop: 8,
    marginBottom: 4,
    alignItems: 'flex-start',
  },
  successTitle: {
    fontSize: 14,
    fontWeight: '700',
    marginBottom: 2,
  },
  successHint: {
    fontSize: 13,
    lineHeight: 18,
  },
});

// ─── Method Toggle Styles ───────────────────────────────────────────────────

const toggleStyles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    borderRadius: 10,
    padding: 3,
    gap: 3,
    marginTop: 8,
    marginBottom: 4,
  },
  tab: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingVertical: 10,
    borderRadius: 8,
  },
  tabText: {
    fontSize: 14,
    fontWeight: '500',
  },
  tabTextActive: {
    fontWeight: '700',
  },
});
