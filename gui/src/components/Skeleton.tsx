/**
 * Skeleton - Loading placeholder components.
 *
 * Provides visual feedback during data loading with animated pulse effect.
 */

import { theme } from "../theme";

interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  borderRadius?: string;
  style?: React.CSSProperties;
}

const baseStyle: React.CSSProperties = {
  backgroundColor: theme.colors.bgTertiary,
  backgroundImage: `linear-gradient(90deg, ${theme.colors.bgTertiary} 0%, ${theme.colors.bgHover} 50%, ${theme.colors.bgTertiary} 100%)`,
  backgroundSize: "200% 100%",
  animation: "skeleton-pulse 1.5s ease-in-out infinite",
};

// Inject keyframes into document head once
if (typeof document !== "undefined") {
  const styleId = "skeleton-keyframes";
  if (!document.getElementById(styleId)) {
    const style = document.createElement("style");
    style.id = styleId;
    style.textContent = `
      @keyframes skeleton-pulse {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
      }
    `;
    document.head.appendChild(style);
  }
}

/**
 * Basic skeleton block.
 */
export function Skeleton({
  width = "100%",
  height = "16px",
  borderRadius = theme.borderRadius.sm,
  style,
}: SkeletonProps) {
  return (
    <div
      style={{
        ...baseStyle,
        width,
        height,
        borderRadius,
        ...style,
      }}
      aria-hidden="true"
    />
  );
}

/**
 * Skeleton for text lines.
 */
export function SkeletonText({
  lines = 3,
  gap = theme.spacing.sm,
}: {
  lines?: number;
  gap?: string;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap }}>
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          width={i === lines - 1 ? "60%" : "100%"}
          height="14px"
        />
      ))}
    </div>
  );
}

/**
 * Skeleton card for list items.
 */
export function SkeletonCard({ style }: { style?: React.CSSProperties }) {
  return (
    <div
      style={{
        backgroundColor: theme.colors.bgSecondary,
        borderRadius: theme.borderRadius.lg,
        padding: theme.spacing.lg,
        border: `1px solid ${theme.colors.bgTertiary}`,
        ...style,
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: theme.spacing.md,
          marginBottom: theme.spacing.md,
        }}
      >
        <Skeleton
          width="40px"
          height="40px"
          borderRadius={theme.borderRadius.full}
        />
        <div style={{ flex: 1 }}>
          <Skeleton width="50%" height="16px" style={{ marginBottom: "8px" }} />
          <Skeleton width="30%" height="12px" />
        </div>
      </div>
      <SkeletonText lines={2} />
    </div>
  );
}

/**
 * Skeleton for job list items.
 */
export function SkeletonJobItem() {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        padding: theme.spacing.lg,
        backgroundColor: theme.colors.bgSecondary,
        borderRadius: theme.borderRadius.md,
        gap: theme.spacing.lg,
      }}
    >
      <Skeleton
        width="60px"
        height="24px"
        borderRadius={theme.borderRadius.full}
      />
      <div style={{ flex: 1 }}>
        <Skeleton width="200px" height="14px" style={{ marginBottom: "6px" }} />
        <Skeleton width="120px" height="12px" />
      </div>
      <Skeleton
        width="80px"
        height="32px"
        borderRadius={theme.borderRadius.sm}
      />
    </div>
  );
}

/**
 * Skeleton for dashboard stats.
 */
export function SkeletonStats({ count = 4 }: { count?: number }) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: `repeat(${count}, 1fr)`,
        gap: theme.spacing.lg,
      }}
    >
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          style={{
            backgroundColor: theme.colors.bgSecondary,
            borderRadius: theme.borderRadius.lg,
            padding: theme.spacing.xl,
            textAlign: "center",
          }}
        >
          <Skeleton
            width="60px"
            height="32px"
            style={{ margin: "0 auto", marginBottom: "12px" }}
          />
          <Skeleton width="80px" height="14px" style={{ margin: "0 auto" }} />
        </div>
      ))}
    </div>
  );
}

/**
 * Empty state component for when there's no data.
 */
export function EmptyState({
  icon = "?",
  title,
  description,
  action,
}: {
  icon?: string;
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: theme.spacing.xxl,
        textAlign: "center",
        minHeight: "200px",
      }}
    >
      <div
        style={{
          fontSize: "48px",
          marginBottom: theme.spacing.lg,
          opacity: 0.5,
        }}
      >
        {icon}
      </div>
      <div
        style={{
          fontSize: theme.fontSize.lg,
          fontWeight: theme.fontWeight.semibold,
          color: theme.colors.textPrimary,
          marginBottom: theme.spacing.sm,
        }}
      >
        {title}
      </div>
      {description && (
        <div
          style={{
            fontSize: theme.fontSize.md,
            color: theme.colors.textSecondary,
            maxWidth: "400px",
            marginBottom: action ? theme.spacing.lg : 0,
          }}
        >
          {description}
        </div>
      )}
      {action}
    </div>
  );
}
