import React, { useState } from 'react';
import {
  View, Text, TextInput, StyleSheet, TouchableOpacity,
  KeyboardAvoidingView, Platform, ScrollView, ActivityIndicator, Alert, Image,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { router } from 'expo-router';
import * as WebBrowser from 'expo-web-browser';
import Svg, { Path } from 'react-native-svg';
import { Camera } from 'lucide-react-native';
import { useTheme } from '../../contexts/ThemeContext';
import { supabase } from '../../lib/supabase';
import { pickImage } from '../../lib/imagePicker';
import Logo from '../../components/Logo';

WebBrowser.maybeCompleteAuthSession();

export default function SignUpScreen() {
  const { colors } = useTheme();
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [step, setStep] = useState<'form' | 'photo'>('form');
  const [photoUri, setPhotoUri] = useState<string | null>(null);
  const [newUserId, setNewUserId] = useState<string | null>(null);

  const handleSignUp = async () => {
    setError('');
    if (!displayName.trim()) {
      setError('Please enter your name.');
      return;
    }
    if (!email.trim()) {
      setError('Please enter your email.');
      return;
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }
    setLoading(true);
    try {
      const { data, error: authError } = await supabase.auth.signUp({
        email: email.trim(),
        password,
        options: {
          data: { display_name: displayName.trim() },
        },
      });
      setLoading(false);
      if (authError) {
        setError(authError.message);
        return;
      }
      // If email confirmation is enabled, user won't have a session yet
      if (data?.user && !data.session) {
        Alert.alert(
          'Check your email',
          `We sent a confirmation link to ${email.trim()}. Tap it to activate your account.`,
          [{ text: 'OK', onPress: () => router.back() }]
        );
        return;
      }
      // If email confirmation is disabled, session exists — show photo step
      if (data?.user && data.session) {
        setNewUserId(data.user.id);
        setStep('photo');
        return;
      }
    } catch (e: any) {
      setLoading(false);
      setError(e.message || 'Something went wrong.');
    }
  };

  const handleGoogleSignUp = async () => {
    setError('');
    setLoading(true);
    try {
      const redirectUrl = 'exp://';
      const { data, error: oauthError } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: redirectUrl,
          skipBrowserRedirect: true,
        },
      });
      if (oauthError) {
        setError(oauthError.message);
        setLoading(false);
        return;
      }
      if (data?.url) {
        const result = await WebBrowser.openAuthSessionAsync(data.url, redirectUrl);
        if (result.type === 'success') {
          const url = new URL(result.url);
          const params = new URLSearchParams(url.hash.substring(1) || url.search.substring(1));
          const access_token = params.get('access_token');
          const refresh_token = params.get('refresh_token');
          if (access_token && refresh_token) {
            await supabase.auth.setSession({ access_token, refresh_token });
          }
        }
      }
    } catch (e: any) {
      setError('Google Sign In failed.');
    }
    setLoading(false);
  };

  const handleAppleSignUp = async () => {
    setError('Apple Sign In requires a development build.');
  };

  async function handlePickPhoto() {
    const uris = await pickImage({ shape: 'circle' });
    if (uris.length > 0) {
      setPhotoUri(uris[0]);
    }
  }

  async function handleFinishWithPhoto() {
    if (!newUserId || !photoUri) return;
    setLoading(true);
    try {
      const ext = photoUri.split('.').pop()?.toLowerCase() || 'jpg';
      const fileName = `avatar.${ext}`;
      const path = `${newUserId}/${fileName}`;
      const formData = new FormData();
      formData.append('', {
        uri: photoUri,
        name: fileName,
        type: `image/${ext === 'jpg' ? 'jpeg' : ext}`,
      } as any);
      await supabase.storage.from('item-photos').upload(path, formData, {
        contentType: 'multipart/form-data',
        upsert: true,
      });
      const { data: urlData } = supabase.storage.from('item-photos').getPublicUrl(path);
      await supabase.from('profiles').update({ avatar_url: urlData.publicUrl }).eq('id', newUserId);
    } catch {}
    setLoading(false);
    router.replace('/');
  }

  function handleSkipPhoto() {
    router.replace('/');
  }

  // ─── Photo step ────────────────────────────────────────────────────────────
  if (step === 'photo') {
    const userInitials = displayName.split(' ').map((w: string) => w[0]).join('').toUpperCase().slice(0, 2) || '?';
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]}>
        <View style={photoStyles.content}>
          <Logo size={36} />
          <Text style={[styles.heroTitle, { color: colors.textPrimary, marginTop: 16 }]}>
            Add a profile picture
          </Text>
          <Text style={[styles.heroSubtitle, { color: colors.textSecondary }]}>
            Optional — you can always change this later
          </Text>

          <TouchableOpacity onPress={handlePickPhoto} activeOpacity={0.7} style={photoStyles.avatarWrap}>
            {photoUri ? (
              <Image source={{ uri: photoUri }} style={photoStyles.avatar} />
            ) : (
              <View style={[photoStyles.avatar, { backgroundColor: colors.primary }]}>
                <Text style={photoStyles.avatarText}>{userInitials}</Text>
              </View>
            )}
            <View style={[photoStyles.cameraBadge, { backgroundColor: colors.accent }]}>
              <Camera size={14} color="#FFFFFF" />
            </View>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.primaryButton, { backgroundColor: colors.accent, opacity: loading ? 0.7 : 1 }]}
            onPress={photoUri ? handleFinishWithPhoto : handlePickPhoto}
            disabled={loading}
            activeOpacity={0.8}
          >
            {loading ? (
              <ActivityIndicator color="#FFFFFF" size="small" />
            ) : (
              <Text style={styles.primaryButtonText}>
                {photoUri ? 'Continue' : 'Choose Photo'}
              </Text>
            )}
          </TouchableOpacity>

          <TouchableOpacity onPress={handleSkipPhoto} style={photoStyles.skipBtn}>
            <Text style={[photoStyles.skipText, { color: colors.textMuted }]}>Skip for now</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.background }]}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <ScrollView
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          <View style={styles.heroSection}>
            <Logo size={36} />
            <Text style={[styles.heroTitle, { color: colors.textPrimary }]}>
              Create your account
            </Text>
            <Text style={[styles.heroSubtitle, { color: colors.textSecondary }]}>
              Set up your AI agents in minutes
            </Text>
          </View>

          {/* OAuth */}
          <View style={styles.oauthSection}>
            <TouchableOpacity
              style={[styles.oauthButton, { backgroundColor: colors.surface }]}
              onPress={handleGoogleSignUp}
              activeOpacity={0.7}
              disabled={loading}
              accessibilityLabel="Sign up with Google"
            >
              <GoogleIcon size={18} />
              <Text style={[styles.oauthButtonText, { color: colors.textPrimary }]}>
                Continue with Google
              </Text>
            </TouchableOpacity>

            {Platform.OS === 'ios' && (
              <TouchableOpacity
                style={[styles.oauthButton, { backgroundColor: colors.surface }]}
                onPress={handleAppleSignUp}
                activeOpacity={0.7}
                disabled={loading}
                accessibilityLabel="Sign up with Apple"
              >
                <AppleIcon size={18} color={colors.textPrimary} />
                <Text style={[styles.oauthButtonText, { color: colors.textPrimary }]}>
                  Continue with Apple
                </Text>
              </TouchableOpacity>
            )}
          </View>

          <View style={styles.dividerRow}>
            <View style={[styles.dividerLine, { backgroundColor: colors.divider }]} />
            <Text style={[styles.dividerText, { color: colors.textMuted }]}>or</Text>
            <View style={[styles.dividerLine, { backgroundColor: colors.divider }]} />
          </View>

          {/* Form */}
          <View style={styles.formSection}>
            <View style={styles.inputGroup}>
              <Text style={[styles.inputLabel, { color: colors.textSecondary }]}>Name</Text>
              <TextInput
                style={[styles.input, { backgroundColor: colors.surface, color: colors.textPrimary }]}
                placeholder="Your name"
                placeholderTextColor={colors.textMuted}
                value={displayName}
                onChangeText={setDisplayName}
                autoCapitalize="words"
                autoComplete="name"
                textContentType="name"
                returnKeyType="next"
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={[styles.inputLabel, { color: colors.textSecondary }]}>Email</Text>
              <TextInput
                style={[styles.input, { backgroundColor: colors.surface, color: colors.textPrimary }]}
                placeholder="you@example.com"
                placeholderTextColor={colors.textMuted}
                value={email}
                onChangeText={setEmail}
                autoCapitalize="none"
                autoComplete="email"
                keyboardType="email-address"
                textContentType="emailAddress"
                returnKeyType="next"
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={[styles.inputLabel, { color: colors.textSecondary }]}>Password</Text>
              <View style={styles.passwordWrap}>
                <TextInput
                  style={[styles.input, styles.passwordInput, { backgroundColor: colors.surface, color: colors.textPrimary }]}
                  placeholder="At least 6 characters"
                  placeholderTextColor={colors.textMuted}
                  value={password}
                  onChangeText={setPassword}
                  secureTextEntry={!showPassword}
                  autoComplete="new-password"
                  textContentType="newPassword"
                  returnKeyType="done"
                  onSubmitEditing={handleSignUp}
                />
                <TouchableOpacity
                  style={styles.showPasswordBtn}
                  onPress={() => setShowPassword(!showPassword)}
                  hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
                  accessibilityLabel={showPassword ? 'Hide password' : 'Show password'}
                >
                  <Text style={[styles.showPasswordText, { color: colors.textMuted }]}>
                    {showPassword ? 'Hide' : 'Show'}
                  </Text>
                </TouchableOpacity>
              </View>
            </View>

            {error ? (
              <Text style={[styles.errorText, { color: colors.destructive }]}>{error}</Text>
            ) : null}

            <TouchableOpacity
              style={[styles.primaryButton, { backgroundColor: colors.accent, opacity: loading ? 0.7 : 1 }]}
              onPress={handleSignUp}
              activeOpacity={0.8}
              disabled={loading}
              accessibilityLabel="Create account"
            >
              {loading ? (
                <ActivityIndicator color="#FFFFFF" size="small" />
              ) : (
                <Text style={styles.primaryButtonText}>Create Account</Text>
              )}
            </TouchableOpacity>
          </View>

          <View style={styles.footerSection}>
            <Text style={[styles.footerText, { color: colors.textMuted }]}>
              Already have an account?{' '}
            </Text>
            <TouchableOpacity
              onPress={() => router.back()}
              hitSlop={{ top: 8, bottom: 8, left: 4, right: 4 }}
            >
              <Text style={[styles.footerLink, { color: colors.accent }]}>Sign In</Text>
            </TouchableOpacity>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

function GoogleIcon({ size = 18 }: { size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <Path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4" />
      <Path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
      <Path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
      <Path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
    </Svg>
  );
}

function AppleIcon({ size = 18, color = '#FFFFFF' }: { size?: number; color?: string }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill={color}>
      <Path d="M17.05 20.28c-.98.95-2.05.88-3.08.4-1.09-.5-2.08-.48-3.24 0-1.44.62-2.2.44-3.06-.4C2.79 15.25 3.51 7.59 9.05 7.31c1.35.07 2.29.74 3.08.8 1.18-.24 2.31-.93 3.57-.84 1.51.12 2.65.72 3.4 1.8-3.12 1.87-2.38 5.98.48 7.13-.57 1.5-1.31 2.99-2.54 4.09zM12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.29 2.58-2.34 4.5-3.74 4.25z" />
    </Svg>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  flex: { flex: 1 },
  scrollContent: {
    flexGrow: 1,
    paddingHorizontal: 24,
    justifyContent: 'center',
    paddingVertical: 40,
  },
  heroSection: { alignItems: 'center', marginBottom: 32, gap: 8 },
  heroTitle: { fontSize: 24, fontWeight: '700', letterSpacing: -0.3, marginTop: 16 },
  heroSubtitle: { fontSize: 15, fontWeight: '400' },
  oauthSection: { gap: 12, marginBottom: 24 },
  oauthButton: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10, height: 48, borderRadius: 12 },
  oauthButtonText: { fontSize: 15, fontWeight: '600' },
  dividerRow: { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 24 },
  dividerLine: { flex: 1, height: 1 },
  dividerText: { fontSize: 13, fontWeight: '500' },
  formSection: { gap: 16 },
  inputGroup: { gap: 6 },
  inputLabel: { fontSize: 13, fontWeight: '600', letterSpacing: 0.2 },
  input: { height: 48, borderRadius: 12, paddingHorizontal: 16, fontSize: 15 },
  passwordWrap: { position: 'relative' as const },
  passwordInput: { paddingRight: 60 },
  showPasswordBtn: { position: 'absolute' as const, right: 16, top: 0, bottom: 0, justifyContent: 'center' as const },
  showPasswordText: { fontSize: 13, fontWeight: '600' },
  errorText: { fontSize: 13, fontWeight: '500' },
  primaryButton: { height: 48, borderRadius: 12, alignItems: 'center' as const, justifyContent: 'center' as const, marginTop: 4 },
  primaryButtonText: { color: '#FFFFFF', fontSize: 16, fontWeight: '700' },
  footerSection: { flexDirection: 'row' as const, justifyContent: 'center' as const, marginTop: 28 },
  footerText: { fontSize: 14, fontWeight: '400' },
  footerLink: { fontSize: 14, fontWeight: '600' },
});

const photoStyles = StyleSheet.create({
  content: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 24,
    gap: 12,
  },
  avatarWrap: {
    position: 'relative',
    marginTop: 24,
    marginBottom: 16,
  },
  avatar: {
    width: 100,
    height: 100,
    borderRadius: 50,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: {
    fontSize: 36,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  cameraBadge: {
    position: 'absolute',
    bottom: 2,
    right: 2,
    width: 32,
    height: 32,
    borderRadius: 16,
    alignItems: 'center',
    justifyContent: 'center',
  },
  skipBtn: {
    paddingVertical: 12,
  },
  skipText: {
    fontSize: 14,
    fontWeight: '500',
  },
});
