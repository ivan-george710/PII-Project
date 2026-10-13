import { copyFile, mkdir, rm } from 'node:fs/promises';

const source = new URL('./', import.meta.url);
const output = new URL('../.presentation-dist/', import.meta.url);
// Publish only presentation assets, never repository data or local review files.
const files = [
  'index.html', 'style.css', 'intro.css', 'component-demos.css',
  'story.js', 'intro.js', 'component-demos.js', 'presentation.js',
  'assets/mark.svg', 'assets/face.png',
];
await rm(output, { recursive: true, force: true });
await mkdir(new URL('assets/', output), { recursive: true });
await Promise.all(files.map(file => copyFile(new URL(file, source), new URL(file, output))));
console.log(`Prepared ${files.length} public presentation assets.`);
