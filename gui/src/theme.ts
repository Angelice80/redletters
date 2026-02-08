/**
 * Red Letters GUI Theme
 *
 * Centralized design tokens for consistent styling.
 * Dark theme optimized for extended reading of Greek text.
 */

export const theme = {
  colors: {
    // Backgrounds
    bgPrimary: "#1a1a2e", // Main background
    bgSecondary: "#2d2d44", // Sidebar, cards
    bgTertiary: "#374151", // Inputs, borders
    bgHover: "#3d3d5c", // Hover states

    // Text
    textPrimary: "#eaeaea", // Main text
    textSecondary: "#9ca3af", // Muted text
    textTertiary: "#6b7280", // Disabled text

    // Brand
    brandRed: "#ef4444", // Red Letters brand
    brandRedLight: "#fecaca", // Light red for text
    brandRedDark: "#7f1d1d", // Dark red for backgrounds

    // Status
    success: "#22c55e",
    successLight: "#86efac",
    warning: "#f59e0b",
    warningLight: "#fcd34d",
    error: "#ef4444",
    errorLight: "#fca5a5",

    // Actions
    primary: "#3b82f6", // Primary buttons
    primaryHover: "#2563eb",
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
    xs: "11px",
    sm: "12px",
    md: "13px",
    base: "14px",
    lg: "16px",
    xl: "18px",
    xxl: "20px",
  },

  fontWeight: {
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },

  shadows: {
    sm: "0 1px 2px rgba(0, 0, 0, 0.3)",
    md: "0 4px 6px rgba(0, 0, 0, 0.4)",
    lg: "0 10px 15px rgba(0, 0, 0, 0.5)",
    xl: "0 20px 60px rgba(0, 0, 0, 0.5)",
  },

  transitions: {
    fast: "0.15s ease",
    normal: "0.2s ease",
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
    fontFamily: "monospace",
    backgroundColor: theme.colors.bgTertiary,
    padding: "2px 6px",
    borderRadius: theme.borderRadius.sm,
    fontSize: theme.fontSize.sm,
  } as React.CSSProperties,
} as const;

export type Theme = typeof theme;
