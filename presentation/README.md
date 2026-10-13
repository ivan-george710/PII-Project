# Automatic architecture film

```sh
python3 -m http.server 8767 --bind 127.0.0.1 --directory presentation
```

Open http://127.0.0.1:8767 and press **Start film** once. Camera movements, engine demonstrations, manager decisions and final architecture reveal run automatically. Nobody needs to operate their section.

The 14 scenes run for 8 minutes 38 seconds by default. The clock button accepts 15–3,600 seconds for each of the six speaking slots and distributes that time across its scenes. Timings are saved locally in the browser. Space pauses/resumes when page body is focused. Timeline, previous/next and replay are contingency/rehearsal tools. Notes (`N`) and fullscreen (`F`) are available. Opening timing/overview or leaving the tab pauses the film.

The sequence is Diljot introduction → Ivan engines 1–2 → Adarsh custom rules → Shambavi audit → Anubhav integration and manager decisions → Diljot architecture and future scope.

Works offline by opening index.html; all scripts, styles and assets are bundled with no CDN/API dependency. Speaker-note links open the actual app/manager if running. The film itself demonstrates synthetic data and makes no real manager decisions or policy changes. Network enforcement and shared-conversation protection are proposed extensions. The current prototype uses no LLM or authentication. Reduced motion keeps completed visual states, fixes packet positions and the document angle, hides the moving routes/caret, and jumps the camera directly.

Browser Print / Save as PDF gives a speaker-notes backup, not a reproduction of the film's animation. Fullscreen film is the primary artifact.

Motion blur is transient: sharp settled views, blur during pans/zooms and local morphs. No sound is played. The film uses DOM/SVG plus a small local Canvas face-pixelation demonstration, with no graphics library or network model.

Local desktop verification completed all 14 scenes in a compressed 90-second rehearsal. The animation-frame counter reported about 60 fps; camera blur reached 5.5px during movement and cleared to 0px at rest. A six-second manager scene showed pending, approved and denied states, and a 3,600-second speaker setting survived reload. These observations apply to the tested local desktop browser.
