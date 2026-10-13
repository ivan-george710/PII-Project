# Architecture presentation

```sh
python3 -m http.server 8767 --bind 127.0.0.1 --directory presentation
```

Open http://127.0.0.1:8767. **Play loops only the current slide. It never advances slides.** Use Next/Previous, arrow keys or the chapter picker when ready.

The top bar contains only the speaker name. Every slide has a short informative heading above its visual; the opening says “Our approach to problem #2” and the final slide says “So, we conclude”. Bottom controls provide playback, the current loop position and slide navigation. The three-dot tools menu contains notes, speed, fullscreen and restart. `N` opens notes; `F` toggles fullscreen; Home/End select the first/last slide. Space toggles playback when the page body is focused. Opening settings/chapters or leaving the tab pauses playback.

Demonstrations repeat in 6–12 seconds at default speed, with a short hold on the result. The speed setting offers 0.75×, 1×, 1.5× and 2× and persists locally. The timeline scrubs only the selected animation; its end cannot change the slide. There is no fixed total speaking time.

The twelve slides begin with a full-system overview, then retain the speaker order: Diljot system overview/problem → Ivan engines/protection → Adarsh rules → Shambavi audit → Anubhav integration/manager → Diljot architecture/future. The problem expands into a wide three-part document/evidence visual inside the architecture’s upload box, which transitions into Ivan’s connected engines. All examples follow the same synthetic quarterly report. Anubhav’s integration view shows only handoffs and manager review; the opening slide shows the complete current architecture, and the next complete reveal belongs to Diljot’s closing section. Extraction and detection stay visible together. A camera transition happens on manual slide changes; within the slide, functional animations loop under fixed framing. The architecture reveal zooms out into the same complete system.

| Component | Repeating demonstration |
| --- | --- |
| Upload | Attach/send original, then protected return after verification. |
| Understand | Native/scanned/embedded content becomes source coordinates and classified findings. |
| Company rules | Exact/regex matching becomes a configured replacement. |
| Protect | Text/face masking retains the chart; saved-copy scanning repairs and rechecks a known remnant. |
| Trace | Source → finding → replacement → revision-bound artifact. |
| Manager | Affected comparison; pending/outage availability → approval → denial blocking. |
| Network | Proposed gateway sanitises before delivery. |
| Shares | Proposed text/face protection before creating a link. |

Camera/local motion uses transient blur and becomes sharp at rest. Reduced motion retains sharp completed states. Mobile controls remain at least 44px. Monochrome SF Pro interface, naturally coloured images and the approved diamond-loop mark are preserved.

All assets are local. Open `index.html` directly for offline use; no CDN, API or model connection is required. Print provides speaker notes. Notes link to the real employee/manager apps if running.

Examples are labeled simulations: no real redaction, policy edits or manager actions occur in the presentation. The app has no LLM/auth, keeps full files and processing local, and sends affected evidence to the manager. Pending/outage downloads stay available; explicit denial blocks. Network and shared-chat interception are future scope. Private policy files are excluded.

Published presentation: https://pii-guard-presentation.catinice.workers.dev/

Update the hosted copy with:

```sh
node presentation/build.mjs
wrangler deploy --config wrangler.presentation.jsonc
```

The build publishes only ten website assets. Wrangler uses its existing local login; credentials and generated output stay outside Git. The frontend regression test covers three loops per slide, pause, timeline-end behavior, manual navigation, and the opening overview plus cropped detail chapters until the closing reveal. The live problem slide completed 26 loops without advancing.
