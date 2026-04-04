/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,jsx,ts,tsx}',
    './components/**/*.{js,jsx,ts,tsx}',
  ],
  presets: [require('nativewind/preset')],
  theme: {
    extend: {
      colors: {
        primary: '#7C3AED',
        'on-primary': '#FFFFFF',
        secondary: '#A78BFA',
        accent: '#16A34A',
        'accent-light': '#DCFCE7',
        background: '#FAF5FF',
        foreground: '#4C1D95',
        muted: '#ECEEF9',
        border: '#DDD6FE',
        destructive: '#DC2626',
      },
    },
  },
  plugins: [],
};
