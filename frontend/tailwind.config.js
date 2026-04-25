/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ['class'],
  content: [
  './app/**/*.{js,ts,jsx,tsx}',
  './components/**/*.{js,ts,jsx,tsx}',
  './store/**/*.{js,ts,jsx,tsx}',
],
  theme: {
    extend: {
      // 🔥 ADD THIS BLOCK (CRITICAL)
      colors: {
        border: 'hsl(var(--border))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',

        muted: 'hsl(var(--muted))',
        'muted-foreground': 'hsl(var(--muted-foreground))',
        // your existing design system
        brand: {
          50:  '#f0faf4',
          100: '#dcf5e6',
          200: '#bbebce',
          300: '#86d9ab',
          400: '#4bbf82',
          500: '#27a363',
          600: '#1a8450',
          700: '#166840',
          800: '#145234',
          900: '#11432b',
        },
        surface: {
          0:   '#ffffff',
          50:  '#f9fafb',
          100: '#f3f4f6',
          200: '#e5e7eb',
        },
        ink: {
          900: '#0f1117',
          700: '#374151',
          500: '#6b7280',
          300: '#d1d5db',
        },
      },

      fontFamily: {
        sans: ['var(--font-geist-sans)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-geist-mono)', 'monospace'],
      },

      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },

      keyframes: {
        'fade-in': {
          '0%':   { opacity: '0', transform: 'translateY(4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-in-left': {
          '0%':   { opacity: '0', transform: 'translateX(-8px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        'scale-in': {
          '0%':   { opacity: '0', transform: 'scale(0.97)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
      },

      animation: {
        'fade-in':       'fade-in 0.2s ease-out',
        'slide-in-left': 'slide-in-left 0.2s ease-out',
        'scale-in':      'scale-in 0.15s ease-out',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
}