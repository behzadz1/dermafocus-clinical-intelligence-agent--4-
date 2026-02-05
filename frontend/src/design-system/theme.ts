/**
 * DermaFocus Design System
 * Centralized theme configuration for consistent UI
 */

// ============================================================================
// COLOR PALETTE
// ============================================================================

export const colors = {
  // Primary - Clinical Trust (Teal)
  primary: {
    50: '#f0fdfa',
    100: '#ccfbf1',
    200: '#99f6e4',
    300: '#5eead4',
    400: '#2dd4bf',
    500: '#14b8a6',
    600: '#0d9488',
    700: '#0f766e',
    800: '#115e59',
    900: '#134e4a',
  },

  // Neutral - Professional Gray
  neutral: {
    50: '#f8fafc',
    100: '#f1f5f9',
    200: '#e2e8f0',
    300: '#cbd5e1',
    400: '#94a3b8',
    500: '#64748b',
    600: '#475569',
    700: '#334155',
    800: '#1e293b',
    900: '#0f172a',
    950: '#020617',
  },

  // Semantic Colors
  success: {
    light: '#ecfdf5',
    main: '#10b981',
    dark: '#059669',
  },
  warning: {
    light: '#fffbeb',
    main: '#f59e0b',
    dark: '#d97706',
  },
  error: {
    light: '#fef2f2',
    main: '#ef4444',
    dark: '#dc2626',
  },
  info: {
    light: '#eff6ff',
    main: '#3b82f6',
    dark: '#2563eb',
  },
};

// ============================================================================
// TYPOGRAPHY
// ============================================================================

export const typography = {
  fontFamily: {
    sans: 'Inter, system-ui, -apple-system, sans-serif',
    mono: 'JetBrains Mono, Menlo, Monaco, monospace',
  },
  fontSize: {
    xs: '0.75rem',     // 12px
    sm: '0.813rem',    // 13px
    base: '0.875rem',  // 14px
    md: '1rem',        // 16px
    lg: '1.125rem',    // 18px
    xl: '1.25rem',     // 20px
    '2xl': '1.5rem',   // 24px
    '3xl': '1.875rem', // 30px
  },
  fontWeight: {
    normal: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
  },
  lineHeight: {
    tight: '1.25',
    normal: '1.5',
    relaxed: '1.625',
  },
};

// ============================================================================
// SPACING
// ============================================================================

export const spacing = {
  0: '0',
  1: '0.25rem',   // 4px
  2: '0.5rem',    // 8px
  3: '0.75rem',   // 12px
  4: '1rem',      // 16px
  5: '1.25rem',   // 20px
  6: '1.5rem',    // 24px
  8: '2rem',      // 32px
  10: '2.5rem',   // 40px
  12: '3rem',     // 48px
  16: '4rem',     // 64px
};

// ============================================================================
// BORDER RADIUS
// ============================================================================

export const borderRadius = {
  none: '0',
  sm: '0.25rem',    // 4px
  md: '0.375rem',   // 6px
  lg: '0.5rem',     // 8px
  xl: '0.75rem',    // 12px
  '2xl': '1rem',    // 16px
  full: '9999px',
};

// ============================================================================
// SHADOWS
// ============================================================================

export const shadows = {
  none: 'none',
  sm: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
  md: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
  lg: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
  xl: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
  glow: '0 0 20px rgb(20 184 166 / 0.15)',
  inner: 'inset 0 2px 4px 0 rgb(0 0 0 / 0.05)',
};

// ============================================================================
// TRANSITIONS
// ============================================================================

export const transitions = {
  fast: '150ms ease',
  normal: '200ms ease',
  slow: '300ms ease',
  spring: '300ms cubic-bezier(0.34, 1.56, 0.64, 1)',
};

// ============================================================================
// Z-INDEX
// ============================================================================

export const zIndex = {
  dropdown: 100,
  modal: 200,
  popover: 300,
  tooltip: 400,
  toast: 500,
};

// ============================================================================
// CONFIDENCE TIERS (Specific to DermaFocus)
// ============================================================================

export const confidenceTiers = {
  high: {
    min: 0.75,
    label: 'High Confidence',
    color: 'emerald',
    bg: 'bg-emerald-50',
    border: 'border-emerald-200',
    text: 'text-emerald-700',
    icon: 'text-emerald-500',
  },
  medium: {
    min: 0.55,
    label: 'Medium Confidence',
    color: 'amber',
    bg: 'bg-amber-50',
    border: 'border-amber-200',
    text: 'text-amber-700',
    icon: 'text-amber-500',
  },
  low: {
    min: 0,
    label: 'Low Confidence',
    color: 'red',
    bg: 'bg-red-50',
    border: 'border-red-200',
    text: 'text-red-600',
    icon: 'text-red-500',
  },
};

export const getConfidenceTier = (confidence: number) => {
  if (confidence >= confidenceTiers.high.min) return confidenceTiers.high;
  if (confidence >= confidenceTiers.medium.min) return confidenceTiers.medium;
  return confidenceTiers.low;
};

// ============================================================================
// COMPONENT VARIANTS
// ============================================================================

export const buttonVariants = {
  primary: 'bg-teal-600 hover:bg-teal-700 text-white shadow-sm',
  secondary: 'bg-white hover:bg-slate-50 text-slate-700 border border-slate-200 shadow-sm',
  ghost: 'bg-transparent hover:bg-slate-100 text-slate-600',
  danger: 'bg-red-600 hover:bg-red-700 text-white shadow-sm',
};

export const cardVariants = {
  default: 'bg-white border border-slate-200 shadow-sm',
  elevated: 'bg-white border border-slate-100 shadow-md',
  interactive: 'bg-white border border-slate-200 shadow-sm hover:shadow-md hover:border-teal-200 transition-all cursor-pointer',
  highlight: 'bg-gradient-to-br from-teal-50 to-white border border-teal-100 shadow-sm',
};

export const badgeVariants = {
  default: 'bg-slate-100 text-slate-700',
  primary: 'bg-teal-50 text-teal-700 border border-teal-200',
  success: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
  warning: 'bg-amber-50 text-amber-700 border border-amber-200',
  error: 'bg-red-50 text-red-600 border border-red-200',
};
