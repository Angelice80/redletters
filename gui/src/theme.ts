/**
 * Red Letters GUI Theme
 *
 * Centralized design tokens for consistent styling.
 * Dark theme optimized for extended reading of Greek text.
 */

export const theme = {
  colors: {
    // Backgrounds (3-layer surface system via CSS custom properties)
    bgPrimary: "var(--rl-bg-panel)", // Panel/sidebar surface
    bgSecondary: "var(--rl-bg-card)", // Cards, controls, elevated
    bgTertiary: "var(--rl-border-strong)", // Input borders, dividers
    bgHover: "var(--rl-bg-hover)", // Hover states

    // Text
    textPrimary: "var(--rl-text)", // Main text
    textSecondary: "var(--rl-text-muted)", // Muted text
    textTertiary: "var(--rl-text-dim)", // Disabled text

    // Brand
    brandRed: "var(--rl-accent)", // Ember red brand accent
    brandRedLight: "#fecaca", // Light red for text
    brandRedDark: "#7f1d1d", // Dark red for backgrounds

    // Status
    success: "var(--rl-success)",
    successLight: "#86efac",
    warning: "var(--rl-warning)",
    warningLight: "#fcd34d",
    error: "var(--rl-error)",
    errorLight: "#fca5a5",

    // Actions
    primary: "var(--rl-primary)", // Primary buttons
    primaryHover: "var(--rl-primary-hover)",
    secondary: "#4b5563", // Secondary buttons
    secondaryHover: "#6b7280",
  },

  spacing: {
    xs: "4px",
    sm: "8px",
    md: "12px",
    lg: "16px",
    xl: "24px",
    xxl: "32px",
  },

  borderRadius: {
    sm: "4px",
    md: "6px",
    lg: "8px",
    xl: "12px",
    full: "9999px",
  },

  fontSize: {
    xs: "var(--rl-fs-xs)", // 11px
    sm: "var(--rl-fs-sm)", // 12px
    md: "var(--rl-fs-base)", // 14px (was 13px, aligned to token scale)
    base: "var(--rl-fs-base)", // 14px
    lg: "var(--rl-fs-md)", // 16px
    xl: "var(--rl-fs-lg)", // 20px
    xxl: "var(--rl-fs-xl)", // 24px
  },

  fontFamily: {
    ui: "var(--rl-font-ui)",
    reading: "var(--rl-font-reading)",
    mono: "var(--rl-font-mono)",
    greek: "var(--rl-font-greek)",
  },

  fontWeight: {
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },

  shadows: {
    sm: "var(--rl-shadow-sm)",
    md: "var(--rl-shadow-md)",
    lg: "var(--rl-shadow-lg)",
    xl: "0 20px 60px rgba(0, 0, 0, 0.5)",
  },

  transitions: {
    fast: "var(--rl-transition-fast)",
    normal: "var(--rl-transition-normal)",
    slow: "0.3s ease",
  },

  zIndex: {
    dropdown: 1000,
    modal: 2000,
    toast: 3000,
  },
} as const;

// Common style patterns
export const commonStyles = {
  // Input field
  input: {
    padding: `${theme.spacing.md} ${theme.spacing.lg}`,
    fontSize: theme.fontSize.base,
    backgroundColor: theme.colors.bgPrimary,
    border: `1px solid ${theme.colors.bgTertiary}`,
    borderRadius: theme.borderRadius.sm,
    color: theme.colors.textPrimary,
    outline: "none",
    transition: `border-color ${theme.transitions.fast}`,
  } as React.CSSProperties,

  // Primary button
  buttonPrimary: {
    padding: `${theme.spacing.md} ${theme.spacing.xl}`,
    fontSize: theme.fontSize.base,
    fontWeight: theme.fontWeight.medium,
    backgroundColor: theme.colors.primary,
    color: "white",
    border: "none",
    borderRadius: theme.borderRadius.md,
    cursor: "pointer",
    transition: `background-color ${theme.transitions.fast}`,
  } as React.CSSProperties,

  // Secondary button
  buttonSecondary: {
    padding: `${theme.spacing.md} ${theme.spacing.xl}`,
    fontSize: theme.fontSize.base,
    fontWeight: theme.fontWeight.medium,
    backgroundColor: theme.colors.secondary,
    color: theme.colors.textPrimary,
    border: "none",
    borderRadius: theme.borderRadius.md,
    cursor: "pointer",
    transition: `background-color ${theme.transitions.fast}`,
  } as React.CSSProperties,

  // Card container
  card: {
    backgroundColor: theme.colors.bgSecondary,
    borderRadius: theme.borderRadius.lg,
    padding: theme.spacing.xl,
    border: `1px solid ${theme.colors.bgTertiary}`,
    borderTop: "1px solid var(--rl-border-subtle)",
    boxShadow: "var(--rl-shadow-md)",
  } as React.CSSProperties,

  // Section label
  label: {
    fontSize: theme.fontSize.sm,
    color: theme.colors.textSecondary,
    textTransform: "uppercase" as const,
    marginBottom: theme.spacing.sm,
    letterSpacing: "0.05em",
  } as React.CSSProperties,

  // Code/monospace
  code: {
    fontFamily: "var(--rl-font-mono)",
    backgroundColor: theme.colors.bgTertiary,
    padding: "2px 6px",
    borderRadius: theme.borderRadius.sm,
    fontSize: theme.fontSize.sm,
  } as React.CSSProperties,
} as const;

export type Theme = typeof theme;
