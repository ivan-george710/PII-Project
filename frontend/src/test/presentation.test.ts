import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it, vi } from 'vitest';

// Exercise the shipped standalone controller, including the real component demos.
// This guards against restoring timed slide advancement during future UI edits.
describe('presentation playback', () => {
  it('loops every slide without navigating; advances only through manual controls', () => {
    const root = resolve(process.cwd(), '../presentation');
    const html = readFileSync(resolve(root, 'index.html'), 'utf8');
    document.body.innerHTML = new DOMParser().parseFromString(html, 'text/html').body.innerHTML;
    window.history.replaceState(null, '', '#0');
    let now = 0;
    let scheduledFrame: FrameRequestCallback | undefined;
    vi.spyOn(performance, 'now').mockImplementation(() => now);
    vi.spyOn(window, 'requestAnimationFrame').mockImplementation(callback => { scheduledFrame = callback; return 1; });
    vi.spyOn(window, 'matchMedia').mockImplementation(query => ({
      matches: false, media: query, onchange: null, addListener: vi.fn(), removeListener: vi.fn(),
      addEventListener: vi.fn(), removeEventListener: vi.fn(), dispatchEvent: () => true,
    }));
    vi.spyOn(console, 'debug').mockImplementation(() => {});
    const resizeCallbacks: ResizeObserverCallback[] = [];
    const BrowserResizeObserver = window.ResizeObserver;
    vi.spyOn(window, 'ResizeObserver').mockImplementation(function (callback: ResizeObserverCallback) {
      resizeCallbacks.push(callback);
      return new BrowserResizeObserver(callback);
    } as unknown as typeof ResizeObserver);
    Object.defineProperty(SVGElement.prototype, 'getTotalLength', { configurable: true, value: () => 100 });
    const script = ['story.js', 'intro.js', 'component-demos.js', 'presentation.js']
      .map(file => readFileSync(resolve(root, file), 'utf8')).join('\n');
    window.eval(script);
    const button = (id: string) => document.getElementById(id) as HTMLButtonElement;
    const tick = (seconds: number) => { now += seconds * 1000; expect(scheduledFrame).toBeDefined(); scheduledFrame!(now); };
    const loopDuration = () => {
      const match = document.getElementById('clock')!.textContent!.match(/\/ (\d+):(\d+)/)!;
      return Number(match[1]) * 60 + Number(match[2]);
    };
    const scenes = ['intro', 'overview', 'understand', 'protect', 'rules', 'audit', 'integration', 'manager', 'architecture', 'network', 'shares', 'closing'];
    const speakers = ['Diljot', 'Diljot', 'Ivan', 'Ivan', 'Adarsh', 'Shambavi', 'Anubhav', 'Anubhav', 'Diljot', 'Diljot', 'Diljot', 'Diljot'];
    expect(document.querySelector('.masthead')!.children).toHaveLength(1);
    button('next').click();
    const problemScrub = document.getElementById('scrub') as HTMLInputElement;
    problemScrub.value = '1000'; problemScrub.dispatchEvent(new Event('input', { bubbles: true }));
    vi.spyOn(Element.prototype, 'getBoundingClientRect').mockReturnValue({
      width: 390, height: 600, top: 0, left: 0, right: 390, bottom: 600, x: 0, y: 0, toJSON: () => ({}),
    });
    resizeCallbacks[0]([], {} as ResizeObserver);
    expect(document.getElementById('intro-stage')!.style.getPropertyValue('--intro-evidence-x')).toBe('0px');
    expect(document.getElementById('intro-stage')!.style.getPropertyValue('--intro-copy-x')).toBe('91px');
    expect(document.body.dataset.cycleProgress).toBe('1.000');
    expect(window.location.hash).toBe('#1');
    button('previous').click();
    button('play').click();
    for (const [index, scene] of scenes.entries()) {
      if (index) button('next').click();
      expect(document.body.dataset.shot).toBe(scene);
      expect(document.getElementById('speaker')!.textContent).toBe(speakers[index]);
      if (index < 8) expect(document.getElementById('world')!.classList.contains('world-overview')).toBe(false);
      if (index === 1) {
        expect(document.getElementById('viewport')).toHaveAttribute('aria-hidden', 'true');
        expect(document.getElementById('intro-stage')).toHaveAttribute('data-intro-scene', '1');
      }
      tick(loopDuration() * 3 + .1);
      expect(document.body.dataset.shot).toBe(scene);
      expect(window.location.hash).toBe(`#${index}`);
      expect(document.body.dataset.loopCount).toBe('3');
    }
    expect(button('next')).toBeDisabled();
    button('next').click();
    expect(window.location.hash).toBe('#11');
    button('play').click();
    const frozen = document.body.dataset.cycleProgress;
    tick(30);
    expect(document.body.dataset.cycleProgress).toBe(frozen);
    const scrub = document.getElementById('scrub') as HTMLInputElement;
    scrub.value = '1000'; scrub.dispatchEvent(new Event('input', { bubbles: true }));
    expect(document.body.dataset.cycleProgress).toBe('1.000');
    expect(window.location.hash).toBe('#11');
    button('play').click(); tick(loopDuration() + .1);
    expect(document.body.dataset.shot).toBe('closing');
    expect(window.location.hash).toBe('#11');
    button('previous').click();
    expect(document.body.dataset.shot).toBe('shares');
    expect(window.location.hash).toBe('#10');
  });
});
