# frontend/src/components

## Files

| Filename | Status | Responsibility |
|---|---|---|
| `analytics.tsx` | Implemented; integration in progress | Preserved real pipeline, funnel, entity distribution, review and finding-location graphics. |
| `artifact-download.tsx` | Implemented; integration in progress | Disable download until engine artifact exists and current manager decision is approved. |
| `evidence.tsx` | Existing | Existing application module; preserve its behavior unless explicitly changed. |
| `product-story.tsx` | Existing | Existing application module; preserve its behavior unless explicitly changed. |
| `review-workspace.tsx` | Existing | Existing application module; preserve its behavior unless explicitly changed. |
| `visual-privacy.tsx` | Existing | Existing application module; preserve its behavior unless explicitly changed. |

Subdirectories contain their own manifests when touched. Engine implementation and phase evidence remain authoritative.

| `brand-mark.tsx` | Implemented; integration in progress | Approved rounded diamond-loop SVG shared by both interfaces. |

| `Strands.jsx` | Implemented; integration in progress | Lazy local WebGL Strands loading animation. |

| `Strands.css` | Implemented; integration in progress | Strands canvas sizing. |

| `Strands.LICENSE.txt` | Implemented; integration in progress | Upstream animation license. |

| `loading-indicator.tsx` | Implemented; integration in progress | Small lazy animation with reduced-motion fallback. |

| `manager-page.tsx` | Implemented; integration in progress | Static mobile manager queue, affected-content comparison, appearance and approval/denial controls. |

| `document-preview.tsx` | Implemented | Real local PDF page renders and Office extracted-text/raster-image comparisons with revision binding, honest error states, keyboard focus and copy feedback. |
| `inspection-page.tsx` | Implemented | Standalone inspection, paginated finding fetch, remote manager link and revision-specific approval polling. |

`chat-document.tsx`: clickable inline original/returned PDF and image previews, or real Office text and embedded media excerpts. Returned content never falls back to source content.
