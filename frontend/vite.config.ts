import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';
import { fileURLToPath, URL } from 'node:url';
export default defineConfig(({mode})=>({
  base: mode==='manager'?'/':'/assets/',
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  server: { port: 5174, strictPort: true, proxy: { '/api': {
    target: 'http://127.0.0.1:8765', changeOrigin: true,
    configure(proxy){proxy.on('proxyReq',(outgoing,incoming)=>{
      // Preserve local Origin checks: translate only the trusted Vite origin.
      if(incoming.headers.origin==='http://127.0.0.1:5174')outgoing.setHeader('Origin','http://127.0.0.1:8765');
    });},
  } } },
  build: { outDir: mode==='manager'?'dist':'../app/web/static', emptyOutDir: mode==='manager', assetsDir: 'bundle', sourcemap: false },
  test: { environment: 'jsdom', globals: true, setupFiles: ['./src/test/setup.ts'], css: false },
}));
