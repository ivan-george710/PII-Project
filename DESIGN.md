# PII Guard interface

Operate mode: familiar, quiet and focused on the employee's conversation. User-provided reference screenshots establish a full-height sidebar and chat surface, generous empty state, compact rounded composer, and restrained neutral theme.

Use system sans-serif, 14–16px body text, 42px desktop / 34px mobile empty-state title, 40px page titles and 24px section headings, consistent 44px touch targets, 12–16px panel radii and pill controls where compact. An accessible arrow icon for Send; other controls remain text-based. Use the approved rounded diamond-loop SVG mark in the workspace sidebar, authentication header and favicon. No gradients, ornamental metric cards, vendor names, or unrelated navigation. Light and dark use CSS semantic tokens, with locally saved system/light/dark preference. Never store credentials in browser storage.

Desktop sidebar is 252px and collapses into a keyboard-accessible drawer on small screens. Conversation width is bounded near 760px. On empty chat, title and composer sit together around the center; populated chats scroll independently and keep composer reachable. Attachments/test samples open above the composer in a bounded, scrollable panel, and show concise labels with details secondary.

Workspace settings use the same shell. Employee creation is inline and creates an employee with a selected immediate manager and a chosen password. The form names the absence of an email invitation and explains how the employee signs in. Existing employees and manager assignment controls remain visible below.

Motion is limited to small control presses and drawer/menu state changes (roughly 180–240ms with a slight spring ease). Respect reduced motion. Loading uses a small monochrome React Bits Strands canvas, with static/text fallbacks; never a full-screen animated background. Auth pages inherit tokens and appearance control.
