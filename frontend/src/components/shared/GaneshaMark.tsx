import React from 'react';

/**
 * Minimal monoline Lord Ganesha silhouette — the application's tiny festival
 * signature (sidebar footer, login hero). Inlined as a component (rather than
 * referenced via <img src=...>) so `stroke="currentColor"` picks up the
 * surrounding text color, matching the rest of the icon system.
 *
 * Source artwork also saved standalone at
 * src/assets/branding/ganesha-line-art.svg
 */
export const GaneshaMark: React.FC<{ className?: string }> = ({ className }) => (
  <svg
    viewBox="0 0 100 100"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    role="img"
    aria-label="Lord Ganesha line art"
    className={className}
  >
    <path d="M42 14 Q50 4 58 14" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    <circle cx="50" cy="8" r="1.6" fill="currentColor" />

    <circle cx="50" cy="30" r="13" stroke="currentColor" strokeWidth="1.6" />

    <path d="M37 22 Q22 20 24 34 Q26 44 38 38" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    <path d="M63 22 Q78 20 76 34 Q74 44 62 38" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />

    <path d="M44 29 q2 -2 4 0" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    <path d="M52 29 q2 -2 4 0" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />

    <path d="M46 37 Q44 46 50 50 Q58 55 52 62 Q48 66 42 63" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />

    <path d="M55 38 L58 44" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />

    <path
      d="M33 47 Q30 60 33 72 Q36 88 50 90 Q64 88 67 72 Q70 60 67 47"
      stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"
    />

    <path d="M30 82 Q50 92 70 82" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />

    <path d="M38 68 Q50 74 62 68" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" opacity="0.7" />
  </svg>
);
