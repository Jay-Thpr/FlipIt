export interface ColorScheme {
  primary: string;
  onPrimary: string;
  accent: string;
  background: string;
  surface: string;
  surfaceRaised: string;
  muted: string;
  destructive: string;
  white: string;
  textPrimary: string;
  textSecondary: string;
  textMuted: string;
  divider: string;
  statusBarStyle: 'light' | 'dark';
}

export const DarkColors: ColorScheme = {
  primary: '#8B5CF6',
  onPrimary: '#FFFFFF',
  accent: '#22C55E',
  background: '#09090B',
  surface: '#151518',
  surfaceRaised: '#1E1E22',
  muted: '#1E1E22',
  destructive: '#EF4444',
  white: '#FFFFFF',
  textPrimary: '#FAFAFA',
  textSecondary: '#A1A1AA',
  textMuted: '#63636E',
  divider: '#ffffff0F',
  statusBarStyle: 'light',
};

export const LightColors: ColorScheme = {
  primary: '#7C3AED',
  onPrimary: '#FFFFFF',
  accent: '#16A34A',
  background: '#F4F4F5',
  surface: '#FFFFFF',
  surfaceRaised: '#EDEDEF',
  muted: '#EDEDEF',
  destructive: '#DC2626',
  white: '#FFFFFF',
  textPrimary: '#18181B',
  textSecondary: '#52525B',
  textMuted: '#A1A1AA',
  divider: '#0000000A',
  statusBarStyle: 'dark',
};

// Legacy fallback — prefer useTheme().colors in components
export const Colors = DarkColors;
