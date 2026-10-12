// Compatibility entry point for the primary React frontend acceptance.
process.env.CADENCE_UI_URL ||= 'http://127.0.0.1:8765';
if (process.argv.includes('--pdf')) process.env.CADENCE_UI_FIXTURE ||= `${process.cwd()}/.private_review_app/phase10b-fixtures/synthetic.pdf`;
await import('./phase10b_browser.mjs');
