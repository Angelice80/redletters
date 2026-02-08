/**
 * Production-grade accessible Tooltip component.
 *
 * S10: Portal to document.body (no clipping from overflow containers).
 *      Viewport collision handling (flip top/bottom, clamp left/right).
 *      Open delay (200ms) to prevent "casino UI" noise.
 * S11: wrapFocus prop makes wrapper keyboard-focusable for disabled children.
 * S12: Unique IDs via useId, aria-describedby only while visible,
 *      role="tooltip", Escape to close, no stuck tooltips.
 */

import {
  useState,
  useRef,
  useId,
  useLayoutEffect,
  useCallback,
  useEffect,
} from "react";
import { createPortal } from "react-dom";

/** px gap between trigger edge and tooltip */
const GAP = 6;
/** px margin from viewport edge */
const VIEWPORT_MARGIN = 8;
/** ms before tooltip appears on hover/focus */
const OPEN_DELAY_MS = 200;

interface TooltipProps {
  /** Tooltip text (keep under ~140 chars) */
  content: string;
  /** Element(s) to wrap */
  children: React.ReactNode;
  /** Preferred position relative to trigger */
  position?: "top" | "bottom";
  /** Max width in px */
  maxWidth?: number;
  /**
   * When true, the wrapper div gets tabIndex={0} so it can receive
   * keyboard focus even when child controls are disabled.
   * Only set this when the child is actually disabled.
   */
  wrapFocus?: boolean;
}

const tooltipStyle: React.CSSProperties = {
  position: "fixed",
  backgroundColor: "#1a1a2e",
  border: "1px solid #4b5563",
  borderRadius: "4px",
  padding: "6px 10px",
  fontSize: "12px",
  color: "#eaeaea",
  whiteSpace: "normal",
  lineHeight: 1.4,
  zIndex: 9999,
  pointerEvents: "none",
  boxShadow: "0 4px 12px rgba(0, 0, 0, 0.3)",
};

export function Tooltip({
  content,
  children,
  position = "top",
  maxWidth = 280,
  wrapFocus = false,
}: TooltipProps) {
  const [open, setOpen] = useState(false);
  const [coords, setCoords] = useState<{
    top: number;
    left: number;
  } | null>(null);

  const triggerRef = useRef<HTMLDivElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const openTimer = useRef(0);
  const tooltipId = useId();

  // --- Show/hide with delay ---
  const showIntent = useCallback(() => {
    window.clearTimeout(openTimer.current);
    openTimer.current = window.setTimeout(() => setOpen(true), OPEN_DELAY_MS);
  }, []);

  const hideIntent = useCallback(() => {
    window.clearTimeout(openTimer.current);
    setOpen(false);
  }, []);

  // Clean up timer on unmount
  useEffect(() => {
    return () => window.clearTimeout(openTimer.current);
  }, []);

  // S12: Escape key closes tooltip
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") hideIntent();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, hideIntent]);

  // --- S10: Compute position via portal (no clipping) ---
  useLayoutEffect(() => {
    if (!open) {
      setCoords(null);
      return;
    }

    const trigger = triggerRef.current;
    const tip = tooltipRef.current;
    if (!trigger || !tip) return;

    const compute = () => {
      const tr = trigger.getBoundingClientRect();
      const tt = tip.getBoundingClientRect();
      const vw = window.innerWidth;
      const vh = window.innerHeight;

      // Flip if preferred position overflows viewport
      let above = position === "top";
      if (above && tr.top - tt.height - GAP < VIEWPORT_MARGIN) {
        above = false;
      } else if (!above && tr.bottom + tt.height + GAP > vh - VIEWPORT_MARGIN) {
        above = true;
      }

      const top = above ? tr.top - tt.height - GAP : tr.bottom + GAP;

      // Center on trigger, then clamp to viewport
      let left = tr.left + tr.width / 2 - tt.width / 2;
      left = Math.max(
        VIEWPORT_MARGIN,
        Math.min(vw - tt.width - VIEWPORT_MARGIN, left),
      );

      setCoords({ top, left });
    };

    // Compute immediately (useLayoutEffect runs before paint)
    compute();

    // Close on scroll or resize — tooltips are transient
    const onScroll = () => hideIntent();
    window.addEventListener("scroll", onScroll, true);
    window.addEventListener("resize", hideIntent);

    return () => {
      window.removeEventListener("scroll", onScroll, true);
      window.removeEventListener("resize", hideIntent);
    };
  }, [open, position, hideIntent]);

  // --- Render ---
  const portal = open
    ? createPortal(
        <div
          ref={tooltipRef}
          id={tooltipId}
          role="tooltip"
          style={{
            ...tooltipStyle,
            top: coords ? coords.top : -9999,
            left: coords ? coords.left : -9999,
            maxWidth,
            // Hidden until positioned to prevent flash
            opacity: coords ? 1 : 0,
          }}
        >
          {content}
        </div>,
        document.body,
      )
    : null;

  return (
    <div
      ref={triggerRef}
      style={{ display: "inline-flex" }}
      onMouseEnter={showIntent}
      onMouseLeave={hideIntent}
      onFocusCapture={showIntent}
      onBlurCapture={hideIntent}
      aria-describedby={open ? tooltipId : undefined}
      // S11: make focusable when child is disabled
      tabIndex={wrapFocus ? 0 : undefined}
    >
      {children}
      {portal}
    </div>
  );
}
