export interface ColorScheme {
  primary: string;
  onPrimary: string;
  secondary: string;
  accent: string;
  accentLight: string;
  background: string;
  surface: string;
  surfaceRaised: string;
  foreground: string;
  muted: string;
  border: string;
  destructive: string;
  white: string;
  textPrimary: string;
  textSecondary: string;
  textMuted: string;
  cardBg: string;
  statusBarStyle: 'light' | 'dark';
}

export const DarkColors: ColorScheme = {
  primary: '#8B5CF6',
  onPrimary: '#FFFFFF',
  secondary: '#A78BFA',
  accent: '#22C55E',
  accentLight: '#14532D',
  background: '#09090B',
  surface: '#18181B',
  surfaceRaised: '#27272A',
  foreground: '#FAFAFA',
  muted: '#27272A',
  border: '#3F3F46',
  destructive: '#EF4444',
  white: '#FFFFFF',
  textPrimary: '#FAFAFA',
  textSecondary: '#A1A1AA',
  textMuted: '#71717A',
  cardBg: '#18181B',
  statusBarStyle: 'light',
};

export const LightColors: ColorScheme = {
  primary: '#7C3AED',
  onPrimary: '#FFFFFF',
  secondary: '#A78BFA',
  accent: '#16A34A',
  accentLight: '#DCFCE7',
  background: '#F4F4F5',
  surface: '#FFFFFF',
  surfaceRaised: '#F4F4F5',
  foreground: '#18181B',
  muted: '#F4F4F5',
  border: '#E4E4E7',
  destructive: '#DC2626',
  white: '#FFFFFF',
  textPrimary: '#18181B',
  textSecondary: '#52525B',
  textMuted: '#A1A1AA',
  cardBg: '#FFFFFF',
  statusBarStyle: 'dark',
};

// Legacy fallback — prefer useTheme().colors in components
export const Colors = DarkColors;
