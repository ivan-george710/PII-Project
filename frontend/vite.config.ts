import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { fileURLToPath, URL } from 'node:url';
import { writeFileSync,readdirSync } from 'node:fs';
export default defineConfig(({mode})=>({
  base: mode==='manager'?'/':'/assets/',
  plugins: [react(), tailwindcss(),{name:'favicon-route',transformIndexHtml(html){return mode==='manager'?html.replace('/assets/favicon.svg','/favicon.svg'):html;}},{name:'static-manifests',closeBundle(){
    if(mode==='manager')return;
    const directory=fileURLToPath(new URL('../app/web/static/',import.meta.url));
    writeFileSync(directory+'index.md','# Built local interface\n\n`index.html` boots the local chat, previews and inspection. `bundle/` contains generated CSS/JS. The Vite build regenerates these manifests and removes obsolete bundles. Hosted manager builds go to frontend/dist.\n');
    const files=readdirSync(directory+'bundle').filter(name=>name!=='index.md');
    writeFileSync(directory+'bundle/index.md','# Generated bundles\n\n'+files.map(name=>'`'+name+'`: '+(name.endsWith('.css')?'compiled UI styles.':'compiled application or lazy animation module.')).join('\n\n')+'\n');
  }}],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  server: { port: 5174, strictPort: true, proxy: { '/api': {
    target: 'http://127.0.0.1:8765', changeOrigin: true,
    configure(proxy){proxy.on('proxyReq',(outgoing,incoming)=>{
      // Preserve local Origin checks: translate only the trusted Vite origin.
      if(incoming.headers.origin==='http://127.0.0.1:5174')outgoing.setHeader('Origin','http://127.0.0.1:8765');
    });},
  } } },
  build: { outDir: mode==='manager'?'dist':'../app/web/static', emptyOutDir: true, assetsDir: 'bundle', sourcemap: false },
  test: { environment: 'jsdom', globals: true, setupFiles: ['./src/test/setup.ts'], css: false },
}));
