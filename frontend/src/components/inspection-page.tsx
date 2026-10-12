import React, { useEffect, useState } from 'react';
import { ArrowLeft, ExternalLink, Sun, Moon, FileText, CheckCircle2, ShieldAlert } from 'lucide-react';
import { BrandMark } from './brand-mark';
import { Pipeline, DetectionFunnel, Entities, ReviewBurden, PrivacyMap } from './analytics';
import { ReviewWorkspace, type Filters } from './review-workspace';
import { DetectorQuality, Timeline, Verification } from './evidence';
import { VisualPrivacy } from './visual-privacy';
import { AIBoundary, AIAccess } from './product-story';
import { ArtifactDownload } from './artifact-download';
import { LoadingIndicator } from './loading-indicator';
import type { DocumentState, Identity, Finding, AuditView, Screen, Decision } from '@/lib/types';
import { api, documentUrl } from '@/lib/api';

interface InspectionPageProps {
  documentId: string;
}

export function InspectionPage({ documentId }: InspectionPageProps) {
  const [state, setState] = useState<DocumentState | null>(null);
  const [identity, setIdentity] = useState<Identity | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [audit, setAudit] = useState<AuditView | null>(null);
  const [screen, setScreen] = useState<Screen>('Overview');
  const [filters, setFilters] = useState<Filters>({
    decision: 'ALL',
    entity: '',
    location: ''
  });
  const [theme, setTheme] = useState(() => window.localStorage?.getItem('pii-theme') ?? 'system');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  useEffect(() => {
    const query = window.matchMedia('(prefers-color-scheme: dark)');
    const apply = () => {
      document.documentElement.dataset.theme = theme === 'system' ? (query.matches ? 'dark' : 'light') : theme;
    };
    apply();
    window.localStorage?.setItem('pii-theme', theme);
    query.addEventListener('change', apply);
    return () => query.removeEventListener('change', apply);
  }, [theme]);

  const loadData = async () => {
    setBusy(true);
    setError('');
    try {
      const [docState, docIdent, docFindings, docAudit] = await Promise.all([
        api<DocumentState>(documentUrl(documentId)),
        api<Identity>(`${documentUrl(documentId)}/review`).catch(() => null),
        api<{ items: Finding[] }>(`${documentUrl(documentId)}/findings?limit=100`).then(r => r.items).catch(() => []),
        api<AuditView>(`${documentUrl(documentId)}/audit`).catch(() => null)
      ]);
      setState(docState);
      setIdentity(docIdent);
      setFindings(docFindings);
      setAudit(docAudit);
    } catch {
      setError('Could not load inspection data for this document. It may have expired or been removed.');
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    void loadData();
  }, [documentId]);

  async function submitFeedback(path: string, payload: unknown) {
    if (!state) return;
    setBusy(true);
    try {
      const updated = await api<DocumentState>(`${documentUrl(state.document_session_id)}/${path}`, {
        method: 'POST',
        body: JSON.stringify(payload)
      });
      setState(updated);
      setNotice('Redaction updated.');
      await loadData();
    } catch {
      setError('Failed to update finding decision.');
    } finally {
      setBusy(false);
    }
  }

  function filter(next: Partial<typeof filters>) {
    setFilters(f => ({ ...f, ...next }));
    setScreen('Review Queue');
  }

  const tabs: Screen[] = ['Overview', 'Review Queue', 'Audit', 'Artifact Verification', 'Detector Quality'];

  return (
    <div className="inspection-page-shell">
      <header className="inspection-topbar">
        <div className="inspection-brand-zone">
          <a href="/" className="back-to-chat-btn" title="Back to Chat">
            <ArrowLeft size={18} />
            <span>Back to Chat</span>
          </a>
          <span className="divider-slash">/</span>
          <a className="brand" href="/">
            <BrandMark />
            <span>PII Guard</span>
          </a>
          <span className="inspection-page-pill">Document Inspection</span>
        </div>

        <div className="inspection-header-right">
          <button className="icon-button" aria-label="Appearance" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
            {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
          </button>
          <a href="/manager" target="_blank" rel="noopener noreferrer" className="manager-page-link">
            <span>Manager Portal</span>
            <ExternalLink size={13} />
          </a>
        </div>
      </header>

      <main className="inspection-main-container">
        {state && (
          <div className="inspection-hero-card">
            <div className="inspection-hero-meta">
              <span className={`format-badge badge-${state.format}`}>{state.format.toUpperCase()}</span>
              <div>
                <h1>{identity?.display_name ?? 'Inspection Report'}</h1>
                <p>
                  Session ID: <code>{state.document_session_id}</code> · Revision {state.revision ?? 0}
                  {identity?.location_count ? ` · ${identity.location_count} ${identity.location_kind}s` : ''}
                </p>
              </div>
            </div>

            <div className="inspection-hero-actions">
              <ArtifactDownload state={state} approval={state.manager_approval} />
            </div>
          </div>
        )}

        {notice && <div className="revision-feedback">{notice}</div>}
        {error && <p role="alert" className="error-banner">{error}</p>}
        {busy && !state && <LoadingIndicator label="Loading inspection…" />}

        <nav className="detail-tabs">
          {tabs.map(tab => (
            <button
              key={tab}
              className={screen === tab ? 'active' : ''}
              onClick={() => {
                if (tab === 'Review Queue') setFilters(f => ({ ...f, decision: 'REVIEW' }));
                setScreen(tab);
              }}
            >
              {({
                'Overview': 'Overview & Pipeline',
                'Review Queue': `Review Queue (${findings.filter(f => f.effective_decision === 'REVIEW').length})`,
                'Audit': 'Audit History',
                'Artifact Verification': 'Artifact Verification',
                'Detector Quality': 'Detector Quality'
              })[tab as Exclude<Screen, 'Documents'>]}
            </button>
          ))}
        </nav>

        <div className="inspection-tab-content">
          {screen === 'Detector Quality' ? (
            <DetectorQuality />
          ) : state && (
            <>
              {screen === 'Overview' && (
                <>
                  <Pipeline state={state} />
                  <AIBoundary state={state} />
                  <AIAccess state={state} />
                  <VisualPrivacy state={state} inspect={() => filter({ entity: 'FACE' })} />
                  <div className="analytics-grid">
                    <DetectionFunnel state={state} onFilter={decision => filter({ decision })} />
                    <ReviewBurden state={state} findings={findings} onReview={() => filter({ decision: 'REVIEW' })} />
                    <Entities findings={findings} onFilter={entity => filter({ entity })} />
                  </div>
                  {identity && (
                    <PrivacyMap
                      findings={findings}
                      identity={identity}
                      onLocation={location => filter({
                        location: String(location),
                        decision: findings.some(f => (f.locations ?? [f.location]).includes(location) && f.effective_decision === 'REVIEW') ? 'REVIEW' : 'ALL'
                      })}
                    />
                  )}
                </>
              )}

              {screen === 'Review Queue' && identity && (
                <ReviewWorkspace
                  key={`${state.document_session_id}-${state.revision}`}
                  state={state}
                  identity={identity}
                  findings={findings}
                  filters={filters}
                  setFilters={setFilters}
                  submit={submitFeedback}
                  busy={busy}
                />
              )}

              {screen === 'Audit' && (
                <Timeline
                  state={state}
                  audit={audit}
                  busy={busy}
                  save={() => void api<DocumentState>(`${documentUrl(state.document_session_id)}/save`, {
                    method: 'POST',
                    body: JSON.stringify({ expected_revision: state.revision })
                  }).catch(() => {})}
                />
              )}

              {screen === 'Artifact Verification' && <Verification state={state} />}
            </>
          )}
        </div>
      </main>
    </div>
  );
}
