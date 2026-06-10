// SVG icon set — single visual language: 24px grid, 1.75 stroke, round caps.
// No emoji used as structural icons (per design system).
const base = {
  width: 24,
  height: 24,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.75,
  strokeLinecap: "round",
  strokeLinejoin: "round",
  "aria-hidden": true,
};

export function IconLogo(props) {
  // Shield + magnifier: scrutiny / verification.
  return (
    <svg {...base} {...props}>
      <path d="M12 3l7 3v5c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z" />
      <circle cx="11" cy="10.5" r="2.5" />
      <path d="M13 12.5l2.5 2.5" />
    </svg>
  );
}

export function IconCheck(props) {
  return (
    <svg {...base} {...props}>
      <path d="M20 6L9 17l-5-5" />
    </svg>
  );
}

export function IconCross(props) {
  return (
    <svg {...base} {...props}>
      <path d="M18 6L6 18M6 6l12 12" />
    </svg>
  );
}

export function IconQuestion(props) {
  return (
    <svg {...base} {...props}>
      <path d="M9.1 9a3 3 0 015.8 1c0 2-3 3-3 3" />
      <path d="M12 17h.01" />
      <circle cx="12" cy="12" r="9" />
    </svg>
  );
}

export function IconScale(props) {
  // Balance scale: evidence weighing.
  return (
    <svg {...base} {...props}>
      <path d="M12 3v18M7 21h10" />
      <path d="M5 7h14M5 7l-2.5 5a3 3 0 005 0L5 7zM19 7l-2.5 5a3 3 0 005 0L19 7z" />
      <path d="M12 5l-5 2M12 5l5 2" />
    </svg>
  );
}

export function IconCpu(props) {
  // ML first-pass.
  return (
    <svg {...base} {...props}>
      <rect x="6" y="6" width="12" height="12" rx="2" />
      <rect x="9.5" y="9.5" width="5" height="5" rx="1" />
      <path d="M9 3v2M15 3v2M9 19v2M15 19v2M3 9h2M3 15h2M19 9h2M19 15h2" />
    </svg>
  );
}

export function IconDoc(props) {
  return (
    <svg {...base} {...props}>
      <path d="M7 3h7l5 5v13H7z" />
      <path d="M14 3v5h5M10 13h6M10 17h6" />
    </svg>
  );
}

export function IconSearch(props) {
  return (
    <svg {...base} {...props}>
      <circle cx="11" cy="11" r="7" />
      <path d="M21 21l-4.3-4.3" />
    </svg>
  );
}

export function IconLink(props) {
  return (
    <svg {...base} {...props}>
      <path d="M10 14a4 4 0 005.7 0l3-3a4 4 0 00-5.7-5.7l-1.5 1.5" />
      <path d="M14 10a4 4 0 00-5.7 0l-3 3a4 4 0 005.7 5.7l1.5-1.5" />
    </svg>
  );
}

export function IconArrow(props) {
  return (
    <svg {...base} {...props}>
      <path d="M5 12h14M13 6l6 6-6 6" />
    </svg>
  );
}

export function IconSpinner(props) {
  return (
    <svg {...base} {...props} className={`spin ${props.className || ""}`}>
      <path d="M12 3a9 9 0 109 9" />
    </svg>
  );
}

export function IconWarning(props) {
  return (
    <svg {...base} {...props}>
      <path d="M12 4l9 16H3l9-16z" />
      <path d="M12 10v4M12 17h.01" />
    </svg>
  );
}

export function IconParse(props) {
  // Final verdict / flag.
  return (
    <svg {...base} {...props}>
      <path d="M5 21V4h12l-2 3 2 3H5" />
    </svg>
  );
}

// Map a node id to its timeline icon.
export const NODE_ICON = {
  ingest: IconDoc,
  ml_classify: IconCpu,
  extract_claims: IconSearch,
  retrieve_evidence: IconLink,
  assess_claims: IconScale,
  fuse: IconParse,
};

// Map a verdict to its icon.
export const VERDICT_ICON = {
  real: IconCheck,
  supported: IconCheck,
  fake: IconCross,
  refuted: IconCross,
  uncertain: IconQuestion,
  unverified: IconQuestion,
};
