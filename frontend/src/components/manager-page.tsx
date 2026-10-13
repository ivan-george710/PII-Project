import { useCallback, useEffect, useRef, useState } from 'react';
import { Moon, Sun, Trash2 } from 'lucide-react';
import { BrandMark } from './brand-mark';
import { LoadingIndicator } from './loading-indicator';
import type { ManagerReport, CustomRule } from '@/lib/types';
import { api } from '@/lib/api';

export function ManagerPage() {
  const [tab, setTab] = useState<'reports' | 'rules'>('reports');
  const [items, setItems] = useState<ManagerReport[]>([]);
  const [selected, setSelected] = useState<ManagerReport | null>(null);
  const selectedRef = useRef<ManagerReport | null>(null);
  selectedRef.current = selected;
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [rules, setRules] = useState<CustomRule[]>([]);
  const [name, setName] = useState('');
  const [pattern, setPattern] = useState('');
  const [isRegex, setIsRegex] = useState(false);
  const [theme, setTheme] = useState(() => window.localStorage?.getItem('pii-theme') ?? 'system');

  useEffect(() => {
    const query = window.matchMedia('(prefers-color-scheme: dark)');
    const apply = () => { document.documentElement.dataset.theme = theme === 'system' ? (query.matches ? 'dark' : 'light') : theme; };
    apply(); window.localStorage?.setItem('pii-theme', theme);
    query.addEventListener('change', apply);
    return () => query.removeEventListener('change', apply);
  }, [theme]);

  const refresh = useCallback(async () => {
    try {
      const result = await api<{ items: ManagerReport[] }>('/api/manager/reports');
      setItems(result.items);
      const current = selectedRef.current;
      const latest = result.items.find(item => item.id === current?.id);
      if (current && latest && (latest.revision !== current.revision || latest.status !== current.status)) {
        setSelected(await api<ManagerReport>(`/api/manager/reports/${current.id}`));
      }
      setError('');
    } catch { setError('Could not load uploads. Try again.'); }
  }, []);
  const refreshRules = useCallback(async () => {
    const result = await api<{ items: CustomRule[] }>('/api/manager/rules');
    setRules(result.items);
  }, []);
  useEffect(() => {
    void refresh();
    const timer = setInterval(() => { if (document.visibilityState === 'visible') void refresh(); }, 10000);
    return () => clearInterval(timer);
  }, [refresh]);
  useEffect(() => {
    if (tab === 'rules') void refreshRules().catch(() => setError('Could not load rules. Try again.'));
  }, [tab, refreshRules]);

  async function open(item: ManagerReport) {
    setBusy(true); setError('');
    try { setSelected(await api<ManagerReport>(`/api/manager/reports/${item.id}`)); }
    catch { setError('Could not open this upload.'); }
    finally { setBusy(false); }
  }
  async function decide(action: 'approved' | 'denied') {
    if (!selected || busy) return;
    setBusy(true); setError('');
    try {
      setSelected(await api<ManagerReport>(`/api/manager/reports/${selected.id}/decision`, {
        method: 'POST', body: JSON.stringify({ revision: selected.revision, artifact_sha256: selected.artifact_sha256, action }),
      }));
      await refresh();
    } catch {
      setError('This result changed or is not ready. Reopen the upload.');
    } finally { setBusy(false); }
  }
  async function addRule(event: React.FormEvent) {
    event.preventDefault(); if (busy || !name.trim() || !pattern.trim()) return;
    setBusy(true); setError('');
    try {
      await api('/api/manager/rules', { method: 'POST', body: JSON.stringify({ name: name.trim(), pattern: pattern.trim(), action: 'redact', is_regex: isRegex }) });
      setName(''); setPattern(''); await refreshRules();
    } catch (failure) { setError(failure instanceof Error ? failure.message : 'Could not save this rule.'); }
    finally { setBusy(false); }
  }
  async function deleteRule(id: string) {
    setBusy(true); setError('');
    try { await api(`/api/manager/rules/${id}`, { method: 'DELETE' }); await refreshRules(); }
    catch { setError('Could not delete this rule. Try again.'); }
    finally { setBusy(false); }
  }
  const statusLabel = (status: ManagerReport['status']) => status === 'pending' ? 'Pending' : status === 'approved' ? 'Approved' : 'Denied';
  return <div className="manager-shell">
    <header className="manager-top">
      <a className="brand" href="/manager"><BrandMark /><span>PII Guard</span></a>
      <nav className="manager-nav" aria-label="Manager navigation">
        <button aria-current={tab === 'reports' ? 'page' : undefined} onClick={() => { setTab('reports'); setSelected(null); }}>Uploads</button>
        <button aria-current={tab === 'rules' ? 'page' : undefined} onClick={() => { setTab('rules'); setSelected(null); }}>Rules</button>
      </nav>
      <button className="icon-button" aria-label="Change appearance" onClick={() => setTheme(document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark')}>{theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}</button>
    </header>
    <main className="manager-content">
      {tab === 'rules' ? <>
        <h1>Redaction rules</h1><p className="muted">Apply to new employee submissions.</p>
        <form className="rule-form" onSubmit={event => void addRule(event)}>
          <label htmlFor="rule-name">Name<input id="rule-name" value={name} onChange={event => setName(event.target.value)} required maxLength={120} /></label>
          <label htmlFor="rule-pattern">Match<input id="rule-pattern" value={pattern} onChange={event => setPattern(event.target.value)} required maxLength={500} /></label>
          <label htmlFor="rule-mode">Match type<select id="rule-mode" value={isRegex ? 'regex' : 'exact'} onChange={event => setIsRegex(event.target.value === 'regex')}><option value="exact">Exact text</option><option value="regex">Regular expression</option></select></label>
          <button type="submit" className="primary" disabled={busy || !name.trim() || !pattern.trim()}>Add rule</button>
        </form>
        <div className="rule-list">{rules.map(rule => <div className="rule-row" key={rule.id}><div><strong>{rule.name}</strong><p>{rule.pattern}</p><small>{rule.is_regex ? 'Regular expression' : 'Exact text'}</small></div><button className="icon-button" aria-label={`Delete rule ${rule.name}`} disabled={busy} onClick={() => void deleteRule(rule.id)}><Trash2 size={18} /></button></div>)}</div>
        {!rules.length && !busy && !error && <p className="muted">No custom rules yet.</p>}
      </> : selected ? <>
        <button className="back-button" onClick={() => setSelected(null)}>Back to uploads</button>
        <h1>{selected.filename}</h1><p className="muted">{new Date(selected.submitted_at).toLocaleString()}</p>
        <div className="decision-bar"><span className="status-pill">{selected.status === 'pending' ? 'Awaiting your decision' : statusLabel(selected.status)}</span><div><button disabled={busy || !selected.ready || selected.status === 'approved'} className="primary" onClick={() => void decide('approved')}>Approve</button><button disabled={busy || selected.status === 'denied'} onClick={() => void decide('denied')}>Deny</button></div></div>
        {!selected.ready && <p className="muted">Finish local review and verification before approval.</p>}
        <div className="comparison-labels"><strong>Original part</strong><strong>Redacted part</strong></div>
        {selected.parts?.length ? selected.parts.map(part => <div className="manager-comparison" key={part.finding_id}><div>{part.original_image ? <img src={part.original_image} alt="Original affected region" /> : <p>{part.original}{part.truncated && '…'}</p>}</div><div>{part.redacted_image ? <img src={part.redacted_image} alt="Redacted affected region" /> : <p>{part.redacted ?? 'Awaiting review'}</p>}</div></div>) : <p>{selected.ready ? 'No findings were reported.' : 'Affected content is unavailable until local processing finishes.'}</p>}
      </> : <>
        <h1>Uploads</h1><p className="muted">Review the affected parts, then approve or deny.</p>
        <div className="manager-list">{items.map(item => <button className="manager-row" key={item.id} onClick={() => void open(item)}><span><strong>{item.filename}</strong><small>{new Date(item.submitted_at).toLocaleString()}</small></span><span className="status-pill">{statusLabel(item.status)}</span></button>)}</div>
        {!items.length && !busy && !error && <p className="muted">New submissions will appear here.</p>}
      </>}
      {busy && <LoadingIndicator label="Updating…" />}
      {error && <div role="alert" className="error-banner">{error}<button onClick={() => { if (tab === 'rules') void refreshRules().catch(() => setError('Could not load rules.')); else void refresh(); }}>Try again</button></div>}
    </main>
  </div>;
}
