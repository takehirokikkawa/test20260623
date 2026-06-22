/**
 * Centralised inline-SVG icon set.
 * All icons use currentColor so they inherit the parent's text colour.
 *
 * Usage:
 *   <Icon name="close" className="w-5 h-5" />
 */

import React from "react";

export type IconName =
  | "close"
  | "plus"
  | "upload"
  | "search"
  | "spinner"
  | "chevron-left"
  | "chevron-right";

interface IconProps {
  name: IconName;
  className?: string;
  /** Override aria-label when the icon is the only accessible label */
  "aria-label"?: string;
  "aria-hidden"?: boolean | "true" | "false";
  strokeWidth?: number;
}

const PATHS: Record<IconName, React.ReactNode> = {
  close: (
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M6 18 18 6M6 6l12 12"
    />
  ),
  plus: (
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M12 4.5v15m7.5-7.5h-15"
    />
  ),
  upload: (
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3m0 0 4.5 4.5M12 3v13.5"
    />
  ),
  search: (
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"
    />
  ),
  // Spinner uses fill (circle track + arc), not stroke
  spinner: (
    <>
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </>
  ),
  "chevron-left": (
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M15.75 19.5 8.25 12l7.5-7.5"
    />
  ),
  "chevron-right": (
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="m8.25 4.5 7.5 7.5-7.5 7.5"
    />
  ),
};

/**
 * Whether the icon uses `fill` rather than `stroke` paths (spinner).
 * For these we render with fill="none" on the SVG root and let the
 * individual path elements carry fill/stroke directly.
 */
const FILL_ICONS = new Set<IconName>(["spinner"]);

export function Icon({
  name,
  className,
  "aria-label": ariaLabel,
  "aria-hidden": ariaHidden,
  strokeWidth = 2,
}: IconProps) {
  const isFill = FILL_ICONS.has(name);

  return (
    <svg
      className={className}
      fill={isFill ? "none" : "none"}
      viewBox="0 0 24 24"
      strokeWidth={isFill ? undefined : strokeWidth}
      stroke={isFill ? undefined : "currentColor"}
      xmlns="http://www.w3.org/2000/svg"
      aria-label={ariaLabel}
      aria-hidden={ariaHidden ?? (ariaLabel ? undefined : true)}
    >
      {PATHS[name]}
    </svg>
  );
}
