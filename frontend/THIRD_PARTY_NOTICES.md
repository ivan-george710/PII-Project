# Selected reusable components

Only public reusable registry components are included. No Bklit Studio source and no repository clone are included.

## Bklit UI

Source: [bklit/bklit-ui](https://github.com/bklit/bklit-ui), pinned commit `f7b3bd2999a5c993863f9cc5523c9cf60b9f3bc2`.
The repository [license boundary](https://github.com/bklit/bklit-ui/blob/f7b3bd2999a5c993863f9cc5523c9cf60b9f3bc2/README.md#license) identifies `packages/ui` and the shadcn registry as MIT; Studio has separate proprietary terms.

Copied public registry files in `src/components/bklit/`:

- `funnel-chart.tsx`: actual pipeline disposition chart.
- `ring-chart.tsx`, `ring-context.tsx`, `ring.tsx`: actual entity distribution rings.
- `animation.ts`, `motion-utils.ts`, `use-mount-progress.ts`, `use-enter-complete.ts`, `chart-formatters.ts`: the required helper closure.

Original code is retained except a documented funnel scaling correction: use the largest stage as the visual denominator when human additions exceed original raw detections; displayed API counts are unchanged. Alias `@/lib/utils` resolves locally. Responsive dimensions, zero-candidate handling, branch labels, keyboard-accessible click overlays, real API data, colors and reduced-motion configuration are supplied by the application wrapper. Unneeded registry helpers/example data/Studio controls are not copied.

Registry sources: `apps/web/public/r/funnel-chart.json`, `ring-chart.json`, `chart-animation.json`, `chart-utils.json`, and `utils.json` at the pinned commit. The MIT notice is retained in `src/components/bklit/LICENSE.txt`.

## shadcn/ui

Source: [shadcn-ui/ui](https://github.com/shadcn-ui/ui), pinned commit `993eb2c3151997ce08a49635c10fd8c8ef3713c7`.
Copied reusable `button`, `card`, `badge`, and `dialog` from `apps/v4/registry/new-york-v4/ui/`, with the MIT notice in `src/components/ui/LICENSE.txt`.

Local changes: `cn` and Button import aliases resolve to this app. Dialog Overlay uses an external-CSS body scroll-lock class rather than Radix's dynamically injected stylesheet. Radix modal focus trapping/dismissal remain; the backend `style-src 'self'` is unchanged. This adaptation was verified with zero browser CSP errors.

Runtime libraries (React, Lucide, Motion, Visx, Radix, clsx, Tailwind Merge/CVA) retain their distributed notices in the locked npm dependencies. The application uses only bundled local assets; no chart CDN/runtime external service is required.
