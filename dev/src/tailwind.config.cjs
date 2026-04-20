/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,jsx}',
    './components/**/*.{js,jsx}',
    './app/**/*.{js,jsx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#00B4A6',
          hover: '#008B7F',
          dark: '#008B7F',
          light: '#E0F7F5',
          subtle: '#F0FDFB',
        },
        accent: {
          DEFAULT: '#FF4D8D',
          hover: '#E6548A',
          light: '#FFE5ED',
          subtle: '#FFF5F8',
        },
        ink: {
          DEFAULT: '#2C3E50',
          soft: '#5A6C7D',
        },
        reserve: {
          DEFAULT: '#FFD600',
        },
        background: {
          DEFAULT: '#FAFBFC',
          secondary: '#F3F4F6',
        },
        text: {
          primary: '#2C3E50',
          secondary: '#5A6C7D',
          tertiary: '#9CA3AF',
        },
        border: {
          DEFAULT: '#E5E7EB',
          light: '#F3F4F6',
        },
      },
      fontFamily: {
        heading: ['var(--font-montserrat)', 'sans-serif'],
        display: ['var(--font-montserrat)', 'sans-serif'],
        accent: ['var(--font-fraunces)', 'Georgia', 'serif'],
        body: ['var(--font-inter)', 'sans-serif'],
      },
      borderRadius: {
        sm: '8px',
        DEFAULT: '12px',
        lg: '16px',
        xl: '20px',
      },
      boxShadow: {
        sm: '0 1px 2px rgba(0, 0, 0, 0.04)',
        md: '0 1px 3px rgba(0, 0, 0, 0.02), 0 4px 16px rgba(0, 0, 0, 0.04)',
        lg: '0 4px 6px rgba(0, 0, 0, 0.02), 0 12px 24px rgba(0, 0, 0, 0.06)',
        xl: '0 8px 16px rgba(0, 0, 0, 0.04), 0 20px 40px rgba(0, 0, 0, 0.08)',
      },
    },
  },
  plugins: [],
};
