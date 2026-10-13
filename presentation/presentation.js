'use strict';

(() => {
  const $ = id => document.getElementById(id);
  const clamp = (value, min = 0, max = 1) => Math.max(min, Math.min(max, value));
  const ease = value => 1 - Math.pow(1 - clamp(value), 4);
  const segment = (value, start, end) => clamp((value - start) / (end - start));
  const clock = seconds => `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const whole = [20, -110, 3430, 1900];
  const nodeBounds = {
    source: [120, 440, 450, 580], extract: [740, 440, 500, 580], detect: [1360, 440, 500, 580],
    rules: [1360, 40, 500, 260], redact: [2070, 440, 500, 580], verify: [2070, 1075, 500, 430],
    audit: [1360, 1220, 500, 430], manager: [2830, 500, 510, 620],
    network: [540, 1930, 730, 480], shares: [1670, 1930, 730, 480]
  };
  const nodes = Object.fromEntries(Object.keys(nodeBounds).map(name => [name,
    $(name === 'network' ? 'gateway' : name === 'shares' ? 'shared-chat' : `${name}-engine`)]));
  // Loop lengths describe demonstrations, never speaking time or slide advancement.
  const shots = [
    { key: 'system', seconds: 12, pipeline: true, rect: whole },
    { key: 'overview', intro: 1, node: 'source', rect: [100, 370, 1840, 620], seconds: 8 },
    { key: 'understand', seconds: 12, rect: [675, 345, 1250, 740], roles: ['extract', 'detect'] },
    { key: 'protect', seconds: 9, rect: [2000, 340, 640, 1230], roles: ['redact', 'verify'] },
    { key: 'rules', seconds: 6, node: 'rules' },
    { key: 'audit', seconds: 7, node: 'audit' },
    { key: 'integration', seconds: 10, pipeline: true, scope: ['redact', 'verify', 'audit', 'manager'], rect: [1310, 315, 2100, 1300] },
    { key: 'manager', seconds: 8, node: 'manager' },
    { key: 'architecture', seconds: 12, pipeline: true, rect: whole },
    { key: 'network', seconds: 8, node: 'network' },
    { key: 'shares', seconds: 8, node: 'shares' },
    { key: 'closing', seconds: 12, pipeline: true, rect: [20, -110, 3430, 2600] }
  ];
  const speedKey = 'pii-presentation-loop-speed-v1';
  const speeds = [.75, 1, 1.5, 2];
  let playbackSpeed = 1;
  try {
    const saved = Number(localStorage.getItem(speedKey));
    if (speeds.includes(saved)) playbackSpeed = saved;
  } catch { /* Offline presentation also works without persistent storage. */ }

  let index = 0, elapsed = 0, playing = false, loops = 0, last = performance.now();
  let camera = { x: 345, y: 730, z: 0 }, target = { ...camera }, velocity = { x: 0, y: 0, z: 0 };
  let frameCount = 0, frameEpoch = performance.now(), lastPaint = 0, dirty = true;
  const viewport = $('viewport'), world = $('world'), carrier = $('artifact-carrier');
  if (!window.PresentationIntro || !window.ComponentDemos) {
    $('scene-title').textContent = 'Presentation files are missing. Open the complete folder.';
    $('play').disabled = true;
    return;
  }
  window.ComponentDemos.mount({ nodes });
  const intro = window.PresentationIntro.mount(nodes.source);
  const demo = options => window.ComponentDemos.render(options);
  const duration = () => shots[index].seconds / playbackSpeed;
  const routeUses = [...document.querySelectorAll('.moving-routes use')];
  const routeLengths = routeUses.map(use => document.querySelector(use.getAttribute('href'))?.getTotalLength() || 100);

  function focusRect(rect, snap = false) {
    const [x, y, width, height] = rect;
    const fitted = Math.min(viewport.clientWidth / width, viewport.clientHeight / height) * .98;
    // The opening overview is explicit; detailed chapters stay cropped until the closing reveal.
    const beforeClosing = index < shots.findIndex(shot => shot.key === 'architecture');
    const scale = beforeClosing && shots[index].key !== 'system' ? Math.max(fitted, viewport.clientWidth / 2750) : fitted;
    target = { x: x + width / 2, y: y + height / 2, z: Math.log(Math.max(.01, scale)) };
    if (reduced.matches || snap) { camera = { ...target }; velocity = { x: 0, y: 0, z: 0 }; }
    dirty = true;
  }
  function frameScene(snap = false) {
    const shot = shots[index];
    if (shot.key === 'overview' && innerWidth < 600) focusRect([100, 370, 640, 860], snap);
    else if (shot.rect) focusRect(shot.rect, snap);
    else if (shot.node) {
      const b = nodeBounds[shot.node], margin = innerWidth < 600 ? 12 : 24;
      focusRect([b[0] - margin, b[1] - 12, b[2] + margin * 2, b[3] + 24], snap);
    }
  }
  function activate(roles = [], overview = false) {
    const active = new Set(typeof roles === 'string' ? [roles] : roles);
    for (const [key, element] of Object.entries(nodes)) element.classList.toggle('active', overview || active.has(key));
    $('understand-group').classList.toggle('active', overview || active.has('extract') || active.has('detect'));
    $('protect-group').classList.toggle('active', overview || active.has('redact') || active.has('verify'));
    world.classList.toggle('world-overview', overview);
  }
  function snapshotNodes() {
    for (const node of Object.keys(nodes)) demo({ node, time: 1, duration: 1, reduced: true, overview: true, playing: false });
  }
  function setPlaying(value) {
    playing = Boolean(value);
    $('play-label').textContent = playing ? 'Pause' : elapsed > 0 ? 'Resume' : 'Play';
    $('play').setAttribute('aria-label', `${playing ? 'Pause' : elapsed > 0 ? 'Resume' : 'Play'} slide animation`);
    $('play').querySelector('path').setAttribute('d', playing ? 'M8 5h3v14H8zm6 0h3v14h-3Z' : 'm8 5 11 7-11 7Z');
    last = performance.now(); dirty = true;
  }
  function select(next, snap = false) {
    index = clamp(Math.trunc(next), 0, shots.length - 1);
    elapsed = 0; loops = 0;
    const shot = shots[index], info = story[index], isIntro = shot.intro != null;
    document.body.dataset.stage = 'architecture';
    nodes.source.classList.toggle('problem-view', isIntro);
    document.body.dataset.shot = shot.key;
    document.body.dataset.loopCount = '0';
    viewport.inert = false;
    viewport.setAttribute('aria-hidden', 'false');
    intro.hidden = !isIntro;
    intro.style.opacity = '1'; intro.style.filter = 'none';
    viewport.style.setProperty('--architecture-opacity', '1');
    const showFuture = ['network', 'shares', 'closing'].includes(shot.key);
    world.classList.toggle('show-future', showFuture);
    nodes.network.setAttribute('aria-hidden', String(!showFuture));
    nodes.shares.setAttribute('aria-hidden', String(!showFuture));
    $('scene-title').textContent = info.heading;
    $('speaker').textContent = info.speaker;
    $('chapter').textContent = info.chapter;
    $('scene-count').textContent = `${index + 1} / ${shots.length}`;
    $('notes-title').textContent = `${info.speaker} · ${info.chapter}`;
    $('notes-text').textContent = info.notes;
    $('demo-label').textContent = shot.key === 'network' || shot.key === 'shares' ? 'Future scope · proposed demonstration' : 'Illustrative demonstration';
    $('context-label').textContent = isIntro ? '' : 'quarterly-report.pdf · synthetic example';
    $('previous').disabled = index === 0;
    $('next').disabled = index === shots.length - 1;
    document.title = `${info.chapter} · PII Guard`;
    history.replaceState(null, '', `#${index}`);
    document.querySelectorAll('#chapters button').forEach((button, i) => button.setAttribute('aria-current', i === index ? 'step' : 'false'));
    snapshotNodes();
    activate(shot.scope || shot.roles || shot.node || [], Boolean(shot.pipeline && !shot.scope));
    frameScene(snap);
    setPlaying(playing);
    renderContent(); renderTransport();
    console.debug('PII presentation scene', index, info.speaker, info.chapter);
  }
  function draw(node, progress) {
    demo({ node, time: progress, duration: 1, reduced: reduced.matches, overview: false, playing });
  }
  function renderPipeline(p) {
    // Send first. Return the protected copy only after saved-output verification.
    const sent = segment(p, .01, .16) * .52;
    const returned = .52 + segment(p, .76, .94) * .48;
    draw('source', p < .76 ? sent : returned);
    draw('extract', segment(p, .10, .31));
    draw('detect', segment(p, .25, .48));
    draw('rules', segment(p, .22, .47));
    draw('redact', segment(p, .45, .65));
    draw('verify', segment(p, .60, .79));
    draw('audit', segment(p, .74, .92));
    // The whole-system loop ends approved. The manager slide separately shows denial.
    demo({ node: 'manager', time: (reduced.matches ? 1 : segment(p, .85, 1)) * .65,
      duration: 1, reduced: false, overview: false, playing: playing && !reduced.matches });
    if (shots[index].key === 'closing') {
      draw('network', segment(p, .10, .60));
      draw('shares', segment(p, .45, .95));
    }
  }
  function handoff(from, to, p) {
    if (p <= 0 || p >= 1 || reduced.matches) { carrier.style.opacity = '0'; return; }
    const a = nodeBounds[from], b = nodeBounds[to], t = ease(p);
    const x = a[0] + a[2] / 2 + (b[0] + b[2] / 2 - a[0] - a[2] / 2) * t;
    const y = a[1] + a[3] / 2 + (b[1] + b[3] / 2 - a[1] - a[3] / 2) * t - Math.sin(p * Math.PI) * 45;
    carrier.style.transform = `translate3d(${x - 35}px,${y - 45}px,0)`;
    carrier.style.opacity = String(Math.sin(p * Math.PI) * .8);
    carrier.style.filter = `blur(${playing ? Math.sin(p * Math.PI) * 2.5 : 0}px)`;
  }
  function renderContent() {
    const shot = shots[index], progress = clamp(elapsed / duration());
    // A short completed hold gives the audience time to read the result before repeating.
    const p = reduced.matches ? 1 : clamp((progress + .025) / .85);
    document.body.dataset.cycleProgress = progress.toFixed(3);
    carrier.style.opacity = '0';
    if (shot.intro != null) {
      window.PresentationIntro.render({ scene: shot.intro, time: elapsed, duration: duration(), reduced: reduced.matches, playing });
    } else if (shot.pipeline) renderPipeline(p);
    else if (shot.key === 'understand') {
      draw('extract', segment(p, 0, .52));
      draw('detect', segment(p, .36, .90));
      handoff('extract', 'detect', segment(p, .42, .55));
    } else if (shot.key === 'protect') {
      draw('redact', segment(p, 0, .55));
      draw('verify', segment(p, .46, .95));
      handoff('redact', 'verify', segment(p, .47, .62));
    } else draw(shot.node, p);
    const resetBlur = playing && !reduced.matches && progress > .975 ? Math.sin((progress - .975) / .025 * Math.PI) * 2 : 0;
    viewport.style.setProperty('--cycle-blur', `${resetBlur.toFixed(2)}px`);
    const relevant = shot.pipeline ? routeUses.map((_, i) => i) : shot.key === 'understand' ? [0, 1] : shot.key === 'protect' ? [2, 4] : shot.key === 'rules' ? [3] : shot.key === 'audit' ? [5, 6] : shot.node === 'manager' ? [6, 7] : [];
    routeUses.forEach((use, i) => {
      use.style.opacity = String(!reduced.matches && relevant.includes(i) ? .75 : 0);
      use.style.strokeDasharray = `22 ${Math.max(1, routeLengths[i] - 22)}`;
      use.style.strokeDashoffset = String(-(elapsed * 180 + i * 30) % routeLengths[i]);
    });
  }
  function renderTransport() {
    const progress = elapsed / duration();
    $('scrub').value = String(Math.round(progress * 1000));
    $('scrub').style.setProperty('--progress', `${progress * 100}%`);
    $('clock').textContent = `Loop ${clock(elapsed)} / ${clock(duration())}`;
  }
  function seekScene(seconds) {
    elapsed = clamp(seconds, 0, duration());
    renderContent(); renderTransport(); setPlaying(playing);
  }
  function frame(now) {
    const rawDt = Math.max(0, (now - last) / 1000), dt = Math.min(.04, rawDt); last = now;
    frameCount++;
    if (now - frameEpoch >= 1000) {
      viewport.dataset.frameRate = (frameCount * 1000 / (now - frameEpoch)).toFixed(1);
      frameCount = 0; frameEpoch = now;
    }
    if (playing) {
      const nextTime = elapsed + rawDt;
      const completed = Math.floor(nextTime / duration());
      elapsed = nextTime % duration();
      if (completed) {
        loops += completed;
        document.body.dataset.loopCount = String(loops);
        console.debug('PII presentation loop', index, loops);
      }
      // Playback deliberately cannot select or navigate to another scene.
    }
    const moving = Object.keys(velocity).some(key => Math.abs(velocity[key]) > .001) || Object.keys(target).some(key => Math.abs(target[key] - camera[key]) > .001);
    if (playing || moving || dirty) {
      if (!reduced.matches) for (let step = 0; step < 4; step++) for (const key of ['x', 'y', 'z']) {
        const h = dt / 4;
        velocity[key] += (75 * (target[key] - camera[key]) - 18 * velocity[key]) * h;
        camera[key] += velocity[key] * h;
      }
      const scale = Math.exp(camera.z);
      const speed = Math.hypot(velocity.x, velocity.y) * scale + Math.abs(velocity.z) * Math.min(viewport.clientWidth, viewport.clientHeight) * .8;
      viewport.style.setProperty('--motion-blur', `${reduced.matches ? 0 : clamp(speed / 320, 0, 5.5).toFixed(2)}px`);
      world.style.transform = `translate3d(${viewport.clientWidth / 2 - camera.x * scale}px,${viewport.clientHeight / 2 - camera.y * scale}px,0) scale(${scale})`;
      if (now - lastPaint > 30 || dirty) { renderContent(); renderTransport(); lastPaint = now; }
      dirty = false;
    }
    requestAnimationFrame(frame);
  }

  function closeTools(focus = false) {
    $('presenter-tools').hidden = true; $('tools-toggle').setAttribute('aria-expanded', 'false');
    if (focus) $('tools-toggle').focus();
  }
  $('tools-toggle').addEventListener('click', () => {
    const open = $('presenter-tools').hidden;
    $('presenter-tools').hidden = !open; $('tools-toggle').setAttribute('aria-expanded', String(open));
    if (open) $('notes-toggle').focus();
  });
  document.addEventListener('click', event => { if (!event.target.closest('#presenter-tools,#tools-toggle')) closeTools(); });
  $('play').addEventListener('click', () => setPlaying(!playing));
  $('scrub').addEventListener('input', event => seekScene(Number(event.target.value) / 1000 * duration()));
  $('next').addEventListener('click', () => select(index + 1));
  $('previous').addEventListener('click', () => select(index - 1));
  $('replay').addEventListener('click', () => { closeTools(); elapsed = 0; loops = 0; document.body.dataset.loopCount = '0'; setPlaying(true); });
  $('notes-toggle').addEventListener('click', () => {
    const open = $('notes').hidden;
    closeTools(); $('notes').hidden = !open;
    $('notes-toggle').setAttribute('aria-expanded', String(open)); if (open) $('notes-close').focus();
  });
  $('notes-close').addEventListener('click', () => { $('notes').hidden = true; $('notes-toggle').setAttribute('aria-expanded', 'false'); $('tools-toggle').focus(); });
  $('chapters').replaceChildren(...story.map((info, i) => {
    const button = document.createElement('button'), title = document.createElement('span'), speaker = document.createElement('small');
    button.dataset.index = String(i); title.textContent = info.chapter; speaker.textContent = info.speaker;
    button.append(title, speaker); return button;
  }));
  $('overview-toggle').addEventListener('click', () => { setPlaying(false); closeTools(); $('overview').showModal(); });
  $('overview-close').addEventListener('click', () => { $('overview').close(); $('overview-toggle').focus(); });
  $('chapters').addEventListener('click', event => {
    const choice = event.target.closest('[data-index]');
    if (choice) { $('overview').close(); select(Number(choice.dataset.index)); $('play').focus(); }
  });
  $('timing-toggle').addEventListener('click', () => {
    setPlaying(false); closeTools(); $('animation-speed').value = String(playbackSpeed); $('timing').showModal();
  });
  $('timing-close').addEventListener('click', () => { $('timing').close(); $('tools-toggle').focus(); });
  $('timing-save').addEventListener('click', () => {
    const choice = Number($('animation-speed').value);
    if (!speeds.includes(choice)) return;
    const progress = elapsed / duration(); playbackSpeed = choice; elapsed = progress * duration();
    try { localStorage.setItem(speedKey, String(choice)); } catch { /* Persistence is optional offline. */ }
    $('timing').close(); setPlaying(false); renderTransport(); $('play').focus();
  });
  $('fullscreen').addEventListener('click', async () => {
    closeTools();
    try { if (document.fullscreenElement) await document.exitFullscreen(); else await document.documentElement.requestFullscreen(); }
    catch { $('fullscreen').setAttribute('aria-label', 'Use browser fullscreen control'); }
  });
  document.addEventListener('fullscreenchange', () => { $('fullscreen').setAttribute('aria-label', document.fullscreenElement ? 'Exit fullscreen' : 'Enter fullscreen'); frameScene(); });
  addEventListener('resize', () => frameScene());
  reduced.addEventListener('change', () => { frameScene(); dirty = true; });
  document.addEventListener('visibilitychange', () => { if (document.hidden) setPlaying(false); });
  document.addEventListener('keydown', event => {
    if (event.target.matches('input,textarea,select') || $('overview').open || $('timing').open) return;
    if (event.key === ' ' && event.target === document.body) { event.preventDefault(); $('play').click(); }
    if (event.key === 'ArrowRight') { event.preventDefault(); $('next').click(); }
    if (event.key === 'ArrowLeft') { event.preventDefault(); $('previous').click(); }
    if (event.key === 'Home') { event.preventDefault(); select(0); }
    if (event.key === 'End') { event.preventDefault(); select(shots.length - 1); }
    if (event.key.toLowerCase() === 'n') $('notes-toggle').click();
    if (event.key.toLowerCase() === 'f') $('fullscreen').click();
    if (event.key === 'Escape') {
      if (!$('notes').hidden) $('notes-close').click();
      else closeTools(true);
    }
  });
  function hashIndex() {
    const hash = location.hash.slice(1), numeric = Number(hash);
    return /^\d+$/.test(hash) && numeric >= 0 && numeric < shots.length ? numeric : Math.max(0, shots.findIndex(shot => shot.key === hash));
  }
  addEventListener('hashchange', () => select(hashIndex()));
  const print = document.createElement('div'); print.id = 'print-deck';
  story.forEach((info, i) => {
    const section = document.createElement('section'), heading = document.createElement('h1'), paragraph = document.createElement('p'), footer = document.createElement('footer');
    section.className = 'print-slide'; heading.textContent = info.chapter; paragraph.textContent = info.notes;
    footer.textContent = `PII Guard · ${info.speaker} · ${i + 1} / ${shots.length}`;
    section.append(heading, paragraph, footer); print.append(section);
  });
  document.body.append(print);
  select(hashIndex(), true); requestAnimationFrame(frame);
})();
