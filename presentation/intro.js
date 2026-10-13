(function () {
  'use strict';

  // The opening is its own stage. The presentation's clock is its only clock.
  let root;
  let refs;
  let observer;
  let lastOptions = {};
  let bounds = { width: 1200, height: 600 };
  const clamp = (value, min = 0, max = 1) => Math.min(max, Math.max(min, value));
  const ease = value => 1 - Math.pow(1 - clamp(value), 4);
  const phase = (time, start, length) => ease((time - start) / length);
  const pulse = (time, start, length) => {
    const value = clamp((time - start) / length);
    return Math.pow(Math.sin(value * Math.PI), 2);
  };
  const arrow = '<svg viewBox="0 0 40 16" aria-hidden="true"><path d="M1 8h36m-7-6 7 6-7 6"/></svg>';
  const chart = '<svg class="intro-business-chart" viewBox="0 0 230 80" role="img" aria-label="Project performance chart"><path class="intro-chart-rules" d="M0 20h230M0 50h230M0 78h230"/><path class="intro-chart-line" d="m2 68 32-7 28 3 31-26 33 6 34-24 34 8 33-19"/></svg>';
  const sensitive = (value, replacement, protectedCopy) => protectedCopy
    ? `<span aria-hidden="true">${value}</span><span class="intro-mask">${replacement}</span>`
    : value;
  const documentBody = protectedCopy => `
    <div class="intro-document-heading"><span>Quarterly report</span><span>Q3</span></div>
    <h3>Project review</h3>
    <div class="intro-document-content">
      <p>By <span class="intro-sensitive intro-person">${sensitive('Dana Ellis', '[PERSON]', protectedCopy)}</span></p>
      <p><span class="intro-sensitive intro-email">${sensitive('dana@example.test', '[EMAIL]', protectedCopy)}</span></p>
      <p><span class="intro-sensitive intro-employee">${sensitive('EMP-2048', '[EMPLOYEE ID]', protectedCopy)}</span></p>
    </div>
    <div class="intro-document-business"><span>Project performance</span>${chart}</div>
    <div class="intro-document-footer"><span>Internal project review</span><span>1</span></div>`;

  function mount(parentElement) {
    if (!parentElement || typeof parentElement.appendChild !== 'function') {
      throw new TypeError('PresentationIntro.mount requires a parent element.');
    }
    if (root && root.parentElement === parentElement) return root;
    if (observer) observer.disconnect();
    if (root) root.remove();
    root = document.createElement('div');
    root.id = 'intro-stage';
    root.className = 'intro-root';
    root.innerHTML = `
      <section class="intro-shot intro-team-shot" aria-labelledby="intro-brand-title">
        <div class="intro-brand-composition">
          <div class="intro-mark" aria-hidden="true">
            <svg viewBox="0 0 120 120">
              <g transform="translate(28 28)">
                <rect class="intro-mark-complete" x="16" y="16" width="32" height="32" rx="10" transform="rotate(45 32 32)"/>
                <g class="intro-mark-fragment intro-mark-north"><rect x="16" y="16" width="32" height="32" rx="10" transform="rotate(45 32 32)" pathLength="160" stroke-dasharray="40 120" stroke-dashoffset="0"/></g>
                <g class="intro-mark-fragment intro-mark-east"><rect x="16" y="16" width="32" height="32" rx="10" transform="rotate(45 32 32)" pathLength="160" stroke-dasharray="40 120" stroke-dashoffset="-40"/></g>
                <g class="intro-mark-fragment intro-mark-south"><rect x="16" y="16" width="32" height="32" rx="10" transform="rotate(45 32 32)" pathLength="160" stroke-dasharray="40 120" stroke-dashoffset="-80"/></g>
                <g class="intro-mark-fragment intro-mark-west"><rect x="16" y="16" width="32" height="32" rx="10" transform="rotate(45 32 32)" pathLength="160" stroke-dasharray="40 120" stroke-dashoffset="-120"/></g>
              </g>
            </svg>
          </div>
          <h2 id="intro-brand-title">PII Guard.</h2>
          <ul class="intro-team" aria-label="Presentation team">
            <li>Diljot</li><li>Ivan</li><li>Adarsh</li><li>Shambavi</li><li>Anubhav</li>
          </ul>
        </div>
      </section>
      <section class="intro-shot intro-overview-shot" aria-labelledby="intro-overview-title" hidden>
        <h2 id="intro-overview-title">One upload.</h2>
        <div class="intro-document-stage">
          <div class="intro-folio intro-upload">
            <span class="intro-folio-label">Original upload</span>
            <article class="intro-document intro-original-document" aria-label="Synthetic original document containing a name, email and employee ID">${documentBody(false)}</article>
            <div class="intro-upload-name"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 3h7l4 4v14H7zM14 3v5h4M10 13h5M10 16h5"/></svg><span>quarterly-report.pdf</span></div>
          </div>
          <div class="intro-folio intro-protected">
            <span class="intro-folio-label">Protected copy</span>
            <article class="intro-document intro-protected-document" aria-label="Protected copy with sensitive values replaced and the business chart preserved">${documentBody(true)}
              <div class="intro-protection-sweep" aria-hidden="true"></div>
            </article>
            <div class="intro-copy-check"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="m4 10 4 4 8-9"/></svg><span>Useful content stays</span></div>
          </div>
          <div class="intro-folio intro-evidence">
            <span class="intro-folio-label">Manager evidence</span>
            <article class="intro-evidence-sheet" aria-label="Manager evidence shows only affected original values and their replacements">
              <div class="intro-evidence-file">quarterly-report.pdf <span>Just now</span></div>
              <div class="intro-evidence-row intro-evidence-person"><span>Dana Ellis</span>${arrow}<strong>[PERSON]</strong></div>
              <div class="intro-evidence-row intro-evidence-email"><span>dana@example.test</span>${arrow}<strong>[EMAIL]</strong></div>
              <p>Affected content only</p>
            </article>
          </div>
          <div class="intro-handoff intro-handoff-copy" aria-hidden="true">${arrow}</div>
          <div class="intro-handoff intro-handoff-evidence" aria-hidden="true">${arrow}</div>
        </div>
        <p class="intro-overview-outcome">A protected copy. A clear record.</p>
      </section>`;
    parentElement.appendChild(root);
    refs = {
      shots: Array.from(root.querySelectorAll('.intro-shot')),
      team: Array.from(root.querySelectorAll('.intro-team li')),
      protectedCopy: root.querySelector('.intro-protected'),
      evidence: root.querySelector('.intro-evidence'),
    };
    const measure = () => {
      const box = root.getBoundingClientRect();
      if (box.width && box.height) {
        const changed = box.width !== bounds.width || box.height !== bounds.height;
        bounds = { width: box.width, height: box.height };
        // A paused slide still needs its current composition to fit a resized viewport.
        if (changed && refs) render(lastOptions);
      }
    };
    measure();
    if (typeof ResizeObserver === 'function') {
      observer = new ResizeObserver(measure);
      observer.observe(root);
    }
    render({ scene: 0, time: 0, duration: 28, reduced: false, playing: false });
    return root;
  }

  function set(name, value) { root.style.setProperty(name, String(value)); }

  function render(options = {}) {
    if (!root) return;
    lastOptions = { ...options };
    const scene = options.scene === 1 || options.scene === 'problem' ? 1 : 0;
    const reduced = Boolean(options.reduced);
    const playing = Boolean(options.playing);
    const duration = Number(options.duration) > 0 ? Number(options.duration) : scene ? 20 : 28;
    const time = clamp(Number(options.time) || 0, 0, duration) / duration * (scene ? 20 : 28);
    refs.shots.forEach((shot, i) => { shot.hidden = i !== scene; });
    root.dataset.introScene = String(scene);
    root.classList.toggle('intro-reduced', reduced);
    root.classList.toggle('intro-playing', playing && !reduced);

    if (scene === 0) {
      // Start from a complete, readable mark, separate its four quarters, then assemble.
      const separation = reduced ? 0 : pulse(time, .15, 4.4);
      const assemble = reduced ? 1 : phase(time, 2.4, 3.4);
      const breath = reduced ? 0 : pulse(time, 10.6, 7.2);
      set('--intro-mark-separation', separation);
      set('--intro-mark-trace', reduced ? 0 : phase(time, 10.6, 3.6) * (1 - phase(time, 15.2, 2.2)));
      set('--intro-mark-turn', reduced ? 0 : separation * 12 + breath * 6);
      set('--intro-brand-scale', 1 + assemble * .035 + breath * .012);
      set('--intro-brand-blur', playing && !reduced ? separation * (1 - assemble) * 1.8 : 0);
      set('--intro-title-y', reduced ? 0 : separation * 8);
      refs.team.forEach((item, i) => {
        const coordinated = reduced ? 0 : pulse(time, .35 + i * .08, 4.25);
        item.style.transform = `translateY(${coordinated * (i % 2 ? -6 : 6)}px)`;
        item.style.filter = `blur(${playing && !reduced ? coordinated * .4 : 0}px)`;
      });
      return;
    }

    const mobile = bounds.width < 600;
    const split = reduced ? 1 : phase(time, 3.5, 3.6);
    const copy = reduced ? 1 : phase(time, 3.6, 2.8);
    const evidence = reduced ? 1 : phase(time, 10.5, 3.4);
    const spread = mobile ? Math.min(91, bounds.width * .235) : Math.min(340, bounds.width * .265);
    const sourceScale = mobile ? 1 - split * .425 : 1 - split * .13;
    const copyScale = mobile ? .82 - split * .245 : .86 + split * .01;
    const sourceY = mobile ? -split * Math.min(103, bounds.height * .16) : -split * 2;
    const copyY = mobile ? sourceY : -split * 2;
    const evidenceY = mobile ? Math.min(155, bounds.height * .25) : 21;
    const mask = reduced ? 1 : phase(time, 6.3, 2.3);
    const motionBlur = playing && !reduced ? pulse(time, 3.5, 3.6) * 2.8 : 0;
    set('--intro-source-x', `${-spread * split}px`);
    set('--intro-source-y', `${sourceY}px`);
    set('--intro-source-scale', sourceScale);
    set('--intro-source-turn', reduced ? -4 : -4 + split * 1.5);
    set('--intro-source-opacity', 1 - split * .2);
    set('--intro-copy-x', `${mobile ? spread * split : 0}px`);
    set('--intro-copy-y', `${copyY}px`);
    set('--intro-copy-scale', copyScale);
    set('--intro-copy-opacity', copy);
    set('--intro-evidence-x', `${mobile ? 0 : spread * evidence}px`);
    set('--intro-evidence-y', `${evidenceY + (1 - evidence) * 42}px`);
    set('--intro-evidence-scale', mobile ? .91 : .97);
    set('--intro-evidence-turn', mobile || reduced ? 0 : 3 * (1 - evidence));
    set('--intro-evidence-opacity', evidence);
    set('--intro-folio-blur', motionBlur);
    set('--intro-evidence-blur', playing && !reduced ? pulse(time, 10.5, 3.4) * 2.8 : 0);
    set('--intro-mask-person', mask);
    set('--intro-mask-email', reduced ? 1 : phase(time, 6.7, 2.3));
    set('--intro-mask-employee', reduced ? 1 : phase(time, 7.1, 2.3));
    set('--intro-sweep', reduced ? 1 : clamp((time - 6.1) / 3));
    set('--intro-sweep-opacity', reduced ? 0 : pulse(time, 6.1, 3));
    set('--intro-check', reduced ? 1 : phase(time, 8.7, 1.2));
    set('--intro-evidence-person', reduced ? 1 : phase(time, 11.3, 1.8));
    set('--intro-evidence-email', reduced ? 1 : phase(time, 11.7, 1.8));
    set('--intro-labels', reduced ? 1 : phase(time, 5.3, 1.5));
    set('--intro-outcome', reduced ? 1 : phase(time, 13.8, 2));
    set('--intro-handoff-copy', reduced || mobile ? 0 : pulse(time, 4.8, 3.5));
    set('--intro-handoff-evidence', reduced || mobile ? 0 : pulse(time, 10.5, 3.4));
    refs.protectedCopy.setAttribute('aria-hidden', copy < .2 ? 'true' : 'false');
    refs.evidence.setAttribute('aria-hidden', evidence < .2 ? 'true' : 'false');
  }

  window.PresentationIntro = Object.freeze({ mount, render });
}());
