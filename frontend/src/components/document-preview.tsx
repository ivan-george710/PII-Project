import React, { useEffect, useState } from 'react';
import { FileText, X, ExternalLink, ChevronLeft, ChevronRight, CheckCircle2, ShieldAlert, Download, Copy, Check } from 'lucide-react';
import type { DocumentState, Identity, PreviewPagesResponse } from '@/lib/types';
import { api, documentUrl } from '@/lib/api';

interface DocumentPreviewProps {
  mode: 'original' | 'redacted';
  state: DocumentState;
  identity?: Identity | null;
  onClose: () => void;
}

export function DocumentPreview({ mode, state, identity, onClose }: DocumentPreviewProps) {
  const [activeTab, setActiveTab] = useState<'visual' | 'text'>(state.format === 'pdf' ? 'visual' : 'text');
  const [data, setData] = useState<PreviewPagesResponse | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    api<PreviewPagesResponse>(`${documentUrl(state.document_session_id)}/preview-pages`)
      .then(res => {
        if (active) {
          setData(res);
          setCurrentPage(1);
        }
      })
      .catch(() => {})
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, [state.document_session_id]);

  const totalPages = data?.total_pages || identity?.location_count || 1;
  const pageItem = data?.pages.find(p => p.page_number === currentPage) || data?.pages[0];

  function copyText(text: string) {
    void navigator.clipboard?.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  function renderFormattedContent(text: string) {
    if (!text) return <p className="preview-empty-text">No text extracted from this {data?.location_kind || 'page'}.</p>;
    
    // Parse tags like [CUSTOM_BLOCKED_001] or [PERSON_001]
    const tagRegex = /\[([A-Z_]+)(?:_\d+)?\]/g;
    const parts = text.split('\n');

    return (
      <div className="preview-formatted-content">
        {parts.map((line, lIdx) => {
          if (!line.trim()) return <div key={lIdx} className="preview-spacer" />;
          
          // Check if line looks like a slide title or heading
          const isTitle = (lIdx === 0 && line.length < 80) || (line.startsWith('#') || (line.toUpperCase() === line && line.length < 60));
          const cleanLine = line.replace(/^#+\s*/, '');

          // Split line by redaction tags to render them with colored pill badges
          const tokens: React.ReactNode[] = [];
          let lastIndex = 0;
          let match: RegExpExecArray | null;
          tagRegex.lastIndex = 0;

          while ((match = tagRegex.exec(cleanLine)) !== null) {
            if (match.index > lastIndex) {
              tokens.push(cleanLine.substring(lastIndex, match.index));
            }
            const entity = match[1];
            const isCustom = entity.startsWith('CUSTOM');
            const isPerson = entity === 'PERSON';
            const isContact = entity === 'EMAIL_ADDRESS' || entity === 'PHONE_NUMBER';
            const pillClass = isCustom ? 'pill-custom' : isPerson ? 'pill-person' : isContact ? 'pill-contact' : 'pill-pii';

            tokens.push(
              <span key={`${lIdx}-${match.index}`} className={`redaction-pill ${pillClass}`} title={`Redacted ${entity}`}>
                {match[0]}
              </span>
            );
            lastIndex = match.index + match[0].length;
          }
          if (lastIndex < cleanLine.length) {
            tokens.push(cleanLine.substring(lastIndex));
          }

          if (isTitle) {
            return <h4 key={lIdx} className="preview-heading">{tokens}</h4>;
          }

          const isBullet = line.trim().startsWith('-') || line.trim().startsWith('•') || /^\d+\./.test(line.trim());
          return (
            <p key={lIdx} className={isBullet ? 'preview-bullet' : 'preview-line'}>
              {isBullet && <span className="bullet-dot">•</span>}
              <span>{tokens}</span>
            </p>
          );
        })}
      </div>
    );
  }

  const formatColorClass = state.format === 'pdf' ? 'badge-pdf' : state.format === 'pptx' ? 'badge-pptx' : 'badge-docx';
  const downloadUrl = `${documentUrl(state.document_session_id)}/${mode === 'original' ? 'original' : 'artifact'}`;

  return (
    <div className="preview-modal-backdrop" role="dialog" aria-modal="true" aria-label={`${mode} document preview`} onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="preview-modal-panel">
        <header className="preview-modal-header">
          <div className="preview-title-block">
            <span className={`format-badge ${formatColorClass}`}>{state.format.toUpperCase()}</span>
            <div>
              <h3>{identity?.display_name ?? `${mode} document`}</h3>
              <p>
                {mode === 'original' ? 'Original document source' : 'Redacted output artifact'} · {totalPages} {data?.location_kind ?? 'section'}{totalPages > 1 ? 's' : ''}
              </p>
            </div>
          </div>

          <div className="preview-header-actions">
            {state.format === 'pdf' && (
              <div className="preview-tab-pills">
                <button className={activeTab === 'visual' ? 'active' : ''} onClick={() => setActiveTab('visual')}>Visual PDF</button>
                <button className={activeTab === 'text' ? 'active' : ''} onClick={() => setActiveTab('text')}>Extracted Text</button>
              </div>
            )}
            <a href={downloadUrl} target="_blank" rel="noopener noreferrer" className="preview-action-btn" title="Open file in a new tab">
              <ExternalLink size={15} />
              <span>Open in new tab</span>
            </a>
            <a href={downloadUrl} download className="preview-action-btn primary" title="Download copy">
              <Download size={15} />
              <span>Download</span>
            </a>
            <button className="icon-button close-btn" aria-label="Close preview" onClick={onClose}>
              <X size={20} />
            </button>
          </div>
        </header>

        <main className="preview-modal-body">
          {activeTab === 'visual' && state.format === 'pdf' ? (
            <div className="preview-iframe-wrapper">
              <iframe
                title={`${mode} document visual preview`}
                src={`${documentUrl(state.document_session_id)}/${mode === 'original' ? 'original' : 'artifact?inline=true'}`}
              />
            </div>
          ) : (
            <div className="preview-content-layout">
              {totalPages > 1 && (
                <aside className="preview-sidebar">
                  <div className="preview-sidebar-header">
                    <span>{data?.location_kind ? data.location_kind.toUpperCase() : 'SECTIONS'}</span>
                    <small>{totalPages} total</small>
                  </div>
                  <div className="preview-nav-list">
                    {Array.from({ length: totalPages }, (_, i) => i + 1).map(num => (
                      <button
                        key={num}
                        className={`preview-nav-item ${currentPage === num ? 'active' : ''}`}
                        onClick={() => setCurrentPage(num)}
                      >
                        <span className="nav-item-num">{num}</span>
                        <span className="nav-item-label">{data?.location_kind === 'slide' ? `Slide ${num}` : `Page ${num}`}</span>
                      </button>
                    ))}
                  </div>
                </aside>
              )}

              <div className="preview-main-content">
                <div className="preview-toolbar">
                  <div className="preview-page-indicator">
                    <button
                      className="icon-button mini"
                      disabled={currentPage <= 1}
                      onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                      aria-label="Previous page"
                    >
                      <ChevronLeft size={16} />
                    </button>
                    <span>{data?.location_kind === 'slide' ? 'Slide' : 'Page'} {currentPage} of {totalPages}</span>
                    <button
                      className="icon-button mini"
                      disabled={currentPage >= totalPages}
                      onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                      aria-label="Next page"
                    >
                      <ChevronRight size={16} />
                    </button>
                  </div>

                  <div className="preview-toolbar-actions">
                    <button
                      className="preview-copy-btn"
                      onClick={() => copyText(mode === 'original' ? (pageItem?.original_text ?? '') : (pageItem?.redacted_text ?? ''))}
                    >
                      {copied ? <Check size={14} className="text-success" /> : <Copy size={14} />}
                      <span>{copied ? 'Copied' : 'Copy page text'}</span>
                    </button>
                  </div>
                </div>

                <div className="preview-card-container">
                  {loading ? (
                    <div className="preview-loading">
                      <p>Loading document content…</p>
                    </div>
                  ) : (
                    <div className="preview-comparison-grid">
                      <div className="preview-pane original-pane">
                        <div className="pane-header">
                          <span className="pane-tag">Original</span>
                          <small>Unredacted source</small>
                        </div>
                        <div className="pane-body">
                          {renderFormattedContent(pageItem?.original_text ?? '')}
                        </div>
                      </div>

                      <div className="preview-pane redacted-pane">
                        <div className="pane-header">
                          <span className="pane-tag success">Redacted Result</span>
                          <small>Protected output</small>
                        </div>
                        <div className="pane-body">
                          {renderFormattedContent(pageItem?.redacted_text ?? '')}
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {data?.redactions && data.redactions.length > 0 && (
                  <footer className="preview-footer-summary">
                    <div className="redactions-badge">
                      <CheckCircle2 size={15} />
                      <strong>{data.redactions.length} PII Replacements Applied</strong>
                    </div>
                    <div className="redactions-tags-list">
                      {Array.from(new Set(data.redactions.map(r => r.entity_type))).map(ent => (
                        <span key={ent} className={`tag-chip ${ent.startsWith('CUSTOM') ? 'chip-custom' : 'chip-standard'}`}>
                          {ent} ({data.redactions.filter(r => r.entity_type === ent).length})
                        </span>
                      ))}
                    </div>
                  </footer>
                )}
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
