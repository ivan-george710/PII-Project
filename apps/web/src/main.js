const status = document.getElementById('status');

try {
  const response = await fetch('/api/health', { cache: 'no-store' });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  const result = await response.json();
  if (result.status !== 'ok' || result.service !== 'pii-guard-api') {
    throw new Error('Unexpected health response');
  }
  status.textContent = 'Backend connected';
} catch {
  status.textContent = 'Backend unavailable';
}
