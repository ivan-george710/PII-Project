'use strict';

(() => {
  const $ = id => document.getElementById(id);
  const clamp = (value, min = 0, max = 1) => Math.max(min, Math.min(max, value));
  const ease = value => 1 - Math.pow(1 - clamp(value), 4);
  const clock = seconds => `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, '0')}`;
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  const nodeBounds = {
    source: [120, 440, 450, 580], extract: [740, 440, 500, 580], detect: [1360, 440, 500, 580],
    rules: [1360, 40, 500, 260], redact: [2070, 440, 500, 580], verify: [2070, 1075, 500, 430],
    audit: [1360, 1220, 500, 430], manager: [2830, 500, 510, 620],
    network: [540, 1930, 730, 480], shares: [1670, 1930, 730, 480]
  };
  const nodes = Object.fromEntries(Object.keys(nodeBounds).map(name => [name,
    $(name === 'network' ? 'gateway' : name === 'shares' ? 'shared-chat' : `${name}-engine`)]));
  const shots = [
    { key: 'intro', intro: 0, seconds: 28 },
    { key: 'overview', intro: 1, seconds: 20 },
    { key: 'understand', seconds: 75, beats: [{ node: 'source', end: .18 }, { node: 'extract', end: .57 }, { node: 'detect', end: 1 }] },
    { key: 'protect', seconds: 50, beats: [{ node: 'redact', end: .58 }, { node: 'verify', end: 1 }] },
    { key: 'rules', seconds: 50, beats: [{ node: 'rules', end: 1 }] },
    { key: 'audit', seconds: 60, beats: [{ node: 'audit', end: 1 }] },
    { key: 'integration', seconds: 45, rect: [20, -110, 3430, 1900] },
    { key: 'manager', seconds: 65, beats: [{ node: 'manager', end: 1 }] },
    { key: 'architecture', seconds: 45, rect: [20, -110, 3430, 1900], heading: 'The whole system.' },
    { key: 'network', seconds: 35, beats: [{ node: 'network', end: 1 }], heading: 'Beyond one interface.' },
    { key: 'shares', seconds: 30, beats: [{ node: 'shares', end: 1 }], heading: 'Before sharing.' },
    { key: 'closing', seconds: 15, rect: [20, -110, 3430, 2600], heading: 'From upload to oversight.' }
  ];
  const groups = [
    { label: 'Diljot · introduction', indices: [0, 1] },
    { label: 'Ivan · engines', indices: [2, 3] },
    { label: 'Adarsh · custom rules', indices: [4] },
    { label: 'Shambavi · audit', indices: [5] },
    { label: 'Anubhav · integration + manager', indices: [6, 7] },
    { label: 'Diljot · architecture + future', indices: [8, 9, 10, 11] }
  ];
  const oldGroups = [[0, 1], [2, 3, 4], [5], [6], [7, 8, 9], [10, 11, 12, 13]];
  const timingKey = 'pii-presentation-component-timing-v2';
  let durations = shots.map(shot => shot.seconds);
  const validDurations = (array, length) => Array.isArray(array) && array.length === length && array.every(n => Number.isFinite(n) && n >= .25 && n <= 3600);
  function setGroupTime(group, seconds) {
    const sum = group.indices.reduce((n, i) => n + shots[i].seconds, 0);
    for (const i of group.indices) durations[i] = shots[i].seconds / sum * seconds;
  }
  try {
    const current = JSON.parse(localStorage.getItem(timingKey));
    if (validDurations(current, shots.length)) durations = current;
    else {
      const legacy = JSON.parse(localStorage.getItem('pii-presentation-timing'));
      if (validDurations(legacy, 14)) groups.forEach((group, i) => setGroupTime(group, clamp(oldGroups[i].reduce((n, j) => n + legacy[j], 0), 15, 3600)));
    }
  } catch { /* A local file presentation also works when storage is unavailable. */ }

  let index = -1, elapsed = 0, playing = false, total = 0, starts = [], last = performance.now();
  let camera = { x: 345, y: 730, z: 0 }, target = { ...camera }, velocity = { x: 0, y: 0, z: 0 };
  let beatKey = '', focusedNode = null, beatStart = 0, beatDuration = 1;
  let carrierFrom = [345, 730], carrierTo = [345, 730], carrierSince = 0;
  let frameCount = 0, frameEpoch = performance.now(), lastPaint = 0, dirty = true;
  const viewport = $('viewport'), world = $('world'), carrier = $('artifact-carrier');
  const intro = window.PresentationIntro?.mount($('film'));
  if (!intro || !window.ComponentDemos) {
    $('scene-title').textContent = 'Presentation files are missing. Open the complete folder.';
    $('play').disabled = true;
    return;
  }
  window.ComponentDemos.mount({ nodes });
  const demo = options => window.ComponentDemos.render(options);
  const routeUses = [...document.querySelectorAll('.moving-routes use')];
  const routeLengths = routeUses.map(use => {
    const path = document.querySelector(use.getAttribute('href'));
    return path?.getTotalLength() || 100;
  });

  function rebuildTiming() {
    total = durations.reduce((a, b) => a + b, 0);
    let sum = 0;
    starts = durations.map(duration => { const start = sum; sum += duration; return start; });
  }
  rebuildTiming();

  function focusRect(rect, snap = false) {
    const [x, y, width, height] = rect;
    const scale = Math.min(viewport.clientWidth / width, viewport.clientHeight / height) * .94;
    target = { x: x + width / 2, y: y + height / 2, z: Math.log(Math.max(.01, scale)) };
    if (reduced.matches || snap) { camera = { ...target }; velocity = { x: 0, y: 0, z: 0 }; }
    dirty = true;
  }
  function focusNode(name, snap = false) {
    const bounds = nodeBounds[name];
    const margin = innerWidth < 600 ? 25 : 75;
    focusRect([bounds[0] - margin, bounds[1] - 50, bounds[2] + margin * 2, bounds[3] + 100], snap);
  }
  function activate(name, overview = false) {
    for (const [key, element] of Object.entries(nodes)) element.classList.toggle('active', overview || key === name);
    $('understand-group').classList.toggle('active', overview || ['extract', 'detect'].includes(name));
    $('protect-group').classList.toggle('active', overview || ['redact', 'verify'].includes(name));
    world.classList.toggle('world-overview', overview);
  }
  function snapshotNodes() {
    for (const node of Object.keys(nodes)) demo({ node, time: 1, duration: 1, reduced: true, overview: true, playing: false });
  }
  function select(next, snap = false) {
    index = clamp(Math.trunc(next), 0, shots.length - 1);
    const shot = shots[index], info = story[index];
    beatKey = '';
    const isIntro = shot.intro != null;
    document.body.dataset.stage = isIntro ? 'intro' : 'architecture';
    document.body.dataset.shot = shot.key;
    viewport.inert = isIntro;
    viewport.setAttribute('aria-hidden', String(isIntro));
    intro.hidden = !isIntro;
    world.classList.toggle('show-future', index >= 9);
    $('scene-title').textContent = shot.heading || '';
    $('speaker').textContent = info.speaker;
    $('chapter').textContent = info.chapter;
    $('scene-count').textContent = `${index + 1} / ${shots.length}`;
    $('notes-title').textContent = `${info.speaker} · ${info.chapter}`;
    $('notes-text').textContent = info.notes;
    $('demo-label').textContent = index === 9 || index === 10 ? 'Future scope · proposed demonstration' : 'Illustrative demonstration';
    $('context-label').textContent = index >= 8 ? 'Full files local · affected evidence remote' : 'No LLM · local redaction';
    document.title = `${info.chapter} · PII Guard`;
    history.replaceState(null, '', `#${index}`);
    document.querySelectorAll('#chapters button').forEach((button, i) => button.setAttribute('aria-current', i === index ? 'step' : 'false'));
    console.debug('PII film scene', index, info.speaker, info.chapter);
    snapshotNodes();
    focusedNode = null;
    if (isIntro) activate(null);
    else if (shot.rect) { activate(null, true); focusRect(shot.rect, snap); }
    else setBeat(elapsed - starts[index], snap);
    dirty = true;
  }
  function setBeat(sceneTime, snap = false) {
    const shot = shots[index];
    if (!shot.beats) return;
    const fraction = clamp(sceneTime / durations[index]);
    const matched = shot.beats.findIndex(beat => fraction < beat.end);
    const beatIndex = matched < 0 ? shot.beats.length - 1 : matched;
    const chosen = shot.beats[beatIndex];
    const previousEnd = beatIndex > 0 ? shot.beats[beatIndex - 1].end : 0;
    const key = `${index}:${beatIndex}`;
    beatStart = previousEnd * durations[index];
    beatDuration = Math.max(.05, (chosen.end - previousEnd) * durations[index]);
    if (key === beatKey) return;
    beatKey = key;
    if (focusedNode && focusedNode !== chosen.node) {
      demo({ node: focusedNode, time: 1, duration: 1, reduced: true, overview: true, playing: false });
      const before = nodeBounds[focusedNode];
      carrierFrom = [before[0] + before[2] / 2, before[1] + before[3] / 2];
    } else carrierFrom = [nodeBounds[chosen.node][0] + 20, nodeBounds[chosen.node][1] + 20];
    focusedNode = chosen.node;
    const after = nodeBounds[focusedNode];
    carrierTo = [after[0] + after[2] / 2, after[1] + after[3] / 2];
    carrierSince = sceneTime;
    activate(focusedNode);
    focusNode(focusedNode, snap);
    console.debug('PII film component', focusedNode);
  }
  function renderContent(sceneTime) {
    const shot = shots[index];
    if (shot.intro != null) {
      intro.hidden = false;
      intro.style.opacity = '1'; intro.style.filter = 'none';
      window.PresentationIntro.render({ scene: shot.intro, time: sceneTime, duration: durations[index], reduced: reduced.matches, playing });
      viewport.style.setProperty('--architecture-opacity', '0');
    } else {
      setBeat(sceneTime);
      const entering = index === 2 && sceneTime < 1.2 && !reduced.matches;
      intro.hidden = !entering;
      if (entering) {
        const p = ease(sceneTime / 1.2);
        window.PresentationIntro.render({ scene: 1, time: durations[1], duration: durations[1], reduced: true, playing: false, leaving: true });
        intro.style.opacity = String(1 - p); intro.style.filter = `blur(${p * 8}px)`;
        viewport.style.setProperty('--architecture-opacity', String(p));
      } else viewport.style.setProperty('--architecture-opacity', '1');
      if (shot.beats) {
        demo({ node: focusedNode, time: clamp(sceneTime - beatStart, 0, beatDuration), duration: beatDuration,
          reduced: reduced.matches, overview: false, playing });
      } else if (shot.key === 'integration') {
        const sequence = ['source', 'extract', 'detect', 'redact', 'verify', 'audit', 'manager'];
        const perNode = durations[index] / sequence.length;
        const step = Math.min(sequence.length - 1, Math.floor(sceneTime / perNode));
        const active = sequence[step];
        activate(active, true);
        for (const [i, node] of sequence.entries()) demo({ node, time: i < step ? 1 : i > step ? 0 : sceneTime - step * perNode,
          duration: i === step ? perNode : 1, reduced: reduced.matches || i !== step, overview: i < step, playing: playing && i === step });
      }
    }
    const age = sceneTime - carrierSince;
    const flight = clamp(age / Math.min(1.4, beatDuration * .25));
    if (shot.intro != null || !shot.beats || reduced.matches || age > 1.4) carrier.style.opacity = '0';
    else {
      const p = ease(flight), x = carrierFrom[0] + (carrierTo[0] - carrierFrom[0]) * p;
      const y = carrierFrom[1] + (carrierTo[1] - carrierFrom[1]) * p - Math.sin(flight * Math.PI) * 90;
      carrier.style.transform = `translate3d(${x - 35}px,${y - 45}px,0) rotate(${Math.sin(flight * Math.PI) * -12}deg)`;
      carrier.style.opacity = String(Math.sin(flight * Math.PI) * .75);
      carrier.style.filter = `blur(${Math.sin(flight * Math.PI) * 2.5}px)`;
    }
    if (!reduced.matches && shot.intro == null) routeUses.forEach((use, i) => {
      const length = routeLengths[i];
      use.style.strokeDasharray = `22 ${Math.max(1, length - 22)}`;
      use.style.strokeDashoffset = String(-(elapsed * 70 + i * 30) % length);
    });
  }
  function renderTransport() {
    const progress = elapsed / total;
    $('scrub').value = String(Math.round(progress * 1000));
    $('scrub').style.setProperty('--progress', `${progress * 100}%`);
    $('clock').textContent = `${clock(elapsed)} / ${clock(total)}`;
  }
  function setPlaying(value) {
    playing = value && elapsed < total;
    $('play-label').textContent = playing ? 'Pause' : elapsed >= total ? 'Replay' : elapsed > 0 ? 'Resume' : 'Start film';
    $('play').setAttribute('aria-label', `${playing ? 'Pause' : elapsed >= total ? 'Replay' : elapsed > 0 ? 'Resume' : 'Start'} automatic presentation`);
    $('play').querySelector('path').setAttribute('d', playing ? 'M8 5h3v14H8zm6 0h3v14h-3Z' : 'm8 5 11 7-11 7Z');
    last = performance.now(); dirty = true;
  }
  function seek(next) {
    elapsed = clamp(next, 0, total);
    const nextIndex = Math.max(0, starts.findLastIndex(start => start <= elapsed));
    select(nextIndex); renderContent(elapsed - starts[index]); renderTransport(); setPlaying(playing);
  }
  function frame(now) {
    const rawDt = Math.max(0, (now - last) / 1000), dt = Math.min(.04, rawDt); last = now;
    frameCount++;
    if (now - frameEpoch >= 1000) {
      viewport.dataset.frameRate = (frameCount * 1000 / (now - frameEpoch)).toFixed(1);
      frameCount = 0; frameEpoch = now;
    }
    if (playing) {
      elapsed = Math.min(total, elapsed + rawDt);
      const next = Math.max(0, starts.findLastIndex(start => start <= elapsed));
      if (next !== index) select(next);
      if (elapsed === total) setPlaying(false);
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
      if (now - lastPaint > 30 || dirty) { renderContent(elapsed - starts[index]); renderTransport(); lastPaint = now; }
      dirty = false;
    }
    requestAnimationFrame(frame);
  }

  $('play').addEventListener('click', () => { if (elapsed >= total) seek(0); setPlaying(!playing); });
  $('scrub').addEventListener('input', event => seek(Number(event.target.value) / 1000 * total));
  $('next').addEventListener('click', () => seek(starts[Math.min(index + 1, shots.length - 1)]));
  $('previous').addEventListener('click', () => seek(starts[Math.max(index - 1, 0)]));
  $('replay').addEventListener('click', () => { seek(starts[index]); setPlaying(true); });
  $('notes-toggle').addEventListener('click', () => {
    const open = $('notes').hidden; $('notes').hidden = !open;
    $('notes-toggle').setAttribute('aria-expanded', String(open)); if (open) $('notes-close').focus();
  });
  $('notes-close').addEventListener('click', () => { $('notes').hidden = true; $('notes-toggle').setAttribute('aria-expanded', 'false'); $('notes-toggle').focus(); });
  $('chapters').replaceChildren(...story.map((info, i) => {
    const button = document.createElement('button'), title = document.createElement('span'), speaker = document.createElement('small');
    button.dataset.index = String(i); title.textContent = info.chapter; speaker.textContent = info.speaker;
    button.append(title, speaker); return button;
  }));
  $('overview-toggle').addEventListener('click', () => { setPlaying(false); $('overview').showModal(); });
  $('overview-close').addEventListener('click', () => { $('overview').close(); $('overview-toggle').focus(); });
  $('chapters').addEventListener('click', event => {
    const choice = event.target.closest('[data-index]');
    if (choice) { $('overview').close(); seek(starts[Number(choice.dataset.index)]); $('play').focus(); }
  });
  $('timing-toggle').addEventListener('click', () => {
    setPlaying(false);
    $('timing-form').replaceChildren(...groups.map((group, i) => {
      const label = document.createElement('label'), input = document.createElement('input');
      label.append(group.label); input.type = 'number'; input.min = '15'; input.max = '3600'; input.step = '1';
      input.value = String(Math.round(group.indices.reduce((n, j) => n + durations[j], 0)));
      input.setAttribute('aria-label', `${group.label}, seconds`); input.dataset.group = String(i); label.append(input); return label;
    }));
    $('timing').showModal();
  });
  $('timing-close').addEventListener('click', () => { $('timing').close(); $('timing-toggle').focus(); });
  $('timing-save').addEventListener('click', () => {
    if (!$('timing-form').reportValidity()) return;
    for (const input of $('timing-form').querySelectorAll('input')) setGroupTime(groups[Number(input.dataset.group)], Number(input.value));
    try { localStorage.setItem(timingKey, JSON.stringify(durations)); } catch { /* Offline use needs no persistent storage. */ }
    rebuildTiming(); elapsed = starts[index]; select(index); renderContent(0); renderTransport();
    $('timing').close(); $('play').focus(); dirty = true;
  });
  $('fullscreen').addEventListener('click', async () => {
    try { if (document.fullscreenElement) await document.exitFullscreen(); else await document.documentElement.requestFullscreen(); }
    catch { $('fullscreen').setAttribute('aria-label', 'Use browser fullscreen control'); }
  });
  document.addEventListener('fullscreenchange', () => {
    $('fullscreen').setAttribute('aria-label', document.fullscreenElement ? 'Exit fullscreen' : 'Enter fullscreen');
    if (focusedNode) focusNode(focusedNode); else if (shots[index].rect) focusRect(shots[index].rect);
  });
  addEventListener('resize', () => { if (focusedNode) focusNode(focusedNode); else if (shots[index].rect) focusRect(shots[index].rect); dirty = true; });
  reduced.addEventListener('change', () => { if (focusedNode) focusNode(focusedNode); else if (shots[index].rect) focusRect(shots[index].rect); dirty = true; });
  document.addEventListener('visibilitychange', () => { if (document.hidden) setPlaying(false); });
  document.addEventListener('keydown', event => {
    if (event.target.matches('input,textarea,select') || $('overview').open || $('timing').open) return;
    if (event.key === ' ' && event.target === document.body) { event.preventDefault(); $('play').click(); }
    if (event.key === 'ArrowRight') { event.preventDefault(); $('next').click(); }
    if (event.key === 'ArrowLeft') { event.preventDefault(); $('previous').click(); }
    if (event.key === 'Home') { event.preventDefault(); seek(0); }
    if (event.key === 'End') { event.preventDefault(); seek(starts[shots.length - 1]); }
    if (event.key.toLowerCase() === 'n') $('notes-toggle').click();
    if (event.key.toLowerCase() === 'f') $('fullscreen').click();
    if (event.key === 'Escape' && !$('notes').hidden) $('notes-close').click();
  });
  function hashIndex() {
    const hash = location.hash.slice(1), numeric = Number(hash);
    return /^\d+$/.test(hash) && numeric >= 0 && numeric < shots.length ? numeric : Math.max(0, shots.findIndex(shot => shot.key === hash));
  }
  addEventListener('hashchange', () => seek(starts[hashIndex()]));
  const print = document.createElement('div'); print.id = 'print-deck';
  story.forEach((info, i) => {
    const section = document.createElement('section'), heading = document.createElement('h1'), paragraph = document.createElement('p'), footer = document.createElement('footer');
    section.className = 'print-slide'; heading.textContent = info.chapter; paragraph.textContent = info.notes;
    footer.textContent = `PII Guard · ${info.speaker} · ${i + 1} / ${shots.length}`;
    section.append(heading, paragraph, footer); print.append(section);
  });
  document.body.append(print);
  index = hashIndex(); elapsed = starts[index]; select(index, true); renderContent(0); renderTransport(); requestAnimationFrame(frame);
})();
