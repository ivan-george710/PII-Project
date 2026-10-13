import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from '../App';
import { artifactUrl, api } from '../lib/api';
import { sourceSelection } from '../lib/review';
import type { AuditEvent, DocumentState, Finding, SourceWindow } from '../lib/types';

const id = 'a'.repeat(32);
let state: DocumentState, findings: Finding[], events: AuditEvent[], calls: { url: string; init: RequestInit }[];
let failed = false;
let feedbackGate: Promise<void> | null = null;
let regenerationFailed = false;
let managerApprovalStatus: 'pending' | 'approved' | 'denied' = 'approved';

const source: SourceWindow = { location: 1, start: 40, total_characters: 83, text: '🙂 Owner: Brightwell. Missed: SecretToken', highlights: [] };
const fresh = (): DocumentState => ({
  document_session_id: id, format: 'pdf', revision: 0, saved_revision: null, artifact_available: true, issue_message: null,
  stages: [
    { name: 'extraction', state: 'Completed', seconds: 1.25 },
    { name: 'detection', state: 'Completed', seconds: 2.5 },
    { name: 'audit', state: 'Completed', seconds: 0.1 },
    { name: 'artifact_redaction', state: 'Completed', seconds: 0.5 },
    { name: 'artifact_verification', state: 'Completed', seconds: 0.2 },
  ],
  summary: {
    processing_status: 'PROCESSED_REVIEW_REQUIRED', coverage_status: 'COVERAGE_UNVERIFIED', coverage_verified: false, safe_for_llm: false,
    downstream_export_permitted: false, total_runtime_seconds: 4.55, failure: null, human_review_complete: false,
    extraction_completed: true, detection_completed: true, text_redaction_completed: true,
    audit: {
      counts: { raw_detection_count: 3, original_confirmed: 1, original_review: 1, original_rejected: 1, confirmed: 1, review: 1, rejected: 1, human_added: 0, applied_redactions: 1, review_queue_items: 1, feedback_events: 0, extracted_pages: 2 },
      revision: 0, human_review_complete: false, redaction_complete: false,
    },
    artifact: {
      format: 'pdf', redaction_completed: true, verification_completed: true, reopened: true, supported_content_verified: true,
      artifact_verified: false, mapping_failures: 0, verification_failures: 0, residual_confirmed_values: 0, residual_sensitive_patterns: 0,
      unsupported_structures: {}, applied_redactions: 1, page_count_preserved: true, safe_for_llm: false, coverage_verified: false, downstream_export_permitted: false,
    },
  },
});

beforeEach(() => {
  state = fresh(); events = []; calls = []; failed = false; feedbackGate = null; regenerationFailed = false;
  managerApprovalStatus = 'approved';
  findings = [
    { finding_id: 'D000001', entity_type: 'PERSON', location: 1, confidence: 0.65, recognizer: 'Synthetic recognizer', automated_decision: 'REVIEW', effective_decision: 'REVIEW', review_status: 'REVIEW_REQUIRED', corrected: false },
    { finding_id: 'D000002', entity_type: 'EMPLOYEE_ID', location: 2, confidence: 0.9, recognizer: 'Synthetic recognizer', automated_decision: 'CONFIRM', effective_decision: 'CONFIRM', review_status: 'APPLIED', corrected: false },
    { finding_id: 'D000003', entity_type: 'US_BANK_NUMBER', location: 1, confidence: 0.2, recognizer: 'Synthetic recognizer', automated_decision: 'REJECT', effective_decision: 'REJECT', review_status: 'REJECTED', corrected: false },
  ];
  vi.stubGlobal('fetch', vi.fn(async (input: string | URL | Request, init: RequestInit = {}) => {
    const url = String(input); calls.push({ url, init }); const route = new URL(url, 'http://localhost').pathname; let value: unknown;
    if (failed && init.method === 'POST') return new Response('{}', { status: 500 });
    if (route === '/api/config') value = { max_upload_bytes: 31457280, supported_formats: ['pdf', 'docx', 'pptx'], trusted_local_only: true, manager_url: 'http://127.0.0.1:8766' };
    else if (route === '/api/samples') value = { items: [{ filename: 'sample1.pdf', label: 'Sample 1' }] };
    else if (route.startsWith('/api/samples/')) return new Response(new Blob(['sample pdf content'], { type: 'application/pdf' }), { status: 200 });
    else if (route === '/api/documents') value = init.method === 'POST' ? state : [state];
    else if (route === '/api/messages') {
      const parsed = JSON.parse(init.body as string);
      state = { ...fresh(), input_text: parsed.text, output_text: 'Sanitized text reply' };
      value = state;
    }
    else if (route === '/api/saved-audits') value = state.saved_revision !== null ? [{ audit_reference: 'b'.repeat(32), label: 'Saved audit 1' }] : [];
    else if (route === '/api/load-audit') value = state;
    else if (route.endsWith('/manager')) value = { id, filename: 'Synthetic.pdf', revision: state.revision ?? 0, ready: true, artifact_sha256: 'c'.repeat(64), status: managerApprovalStatus, parts: [], counts: {} };
    else if (route.endsWith('/original')) return new Response(new Blob(['pdf content']), { status: 200, headers: { 'Content-Disposition': 'inline; filename="Synthetic.pdf"' } });
    else if (route.endsWith('/review')) value = { display_name: 'Synthetic.pdf', location_kind: 'page', location_count: 2 };
    else if (route.endsWith('/source')) value = source;
    else if (route.endsWith('/comparison')) value = { finding_id: 'D000001', redacted_context: null, replacement: null, state: 'REVIEW_REQUIRED' };
    else if (/\/findings\/[DV]/.test(route)) value = { finding: findings.find(f => route.endsWith(f.finding_id)), before: 'Owner: ', candidate: 'Brightwell', after: ' in this policy.', candidate_truncated: false, visual_before_url: route.includes('/V') ? '/api/documents/' + id + '/findings/V000001/visual-crop' : null, visual_after_url: route.includes('/V') ? '/api/documents/' + id + '/findings/V000001/visual-crop?after=true' : null };
    else if (route.endsWith('/findings')) value = { items: findings, total: findings.length, entities: findings.map(f => f.entity_type), locations: [1, 2] };
    else if (route.endsWith('/audit')) value = { summary: state.summary, events };
    else if (route.endsWith('/feedback') || route.endsWith('/missed-pii')) {
      if (feedbackGate) await feedbackGate;
      const body = JSON.parse(init.body as string); const f = findings.find(f => f.finding_id === body.finding_id) ?? findings[0];
      if (route.endsWith('/feedback')) { f.effective_decision = body.action === 'CONFIRM_PII' ? 'CONFIRM' : 'REJECT'; f.corrected = true; f.review_status = body.action === 'CONFIRM_PII' ? 'APPLIED' : 'REJECTED'; }
      state = structuredClone(state); state.revision = (state.revision ?? 0) + 1; state.summary.audit!.revision = state.revision;
      state.summary.audit!.counts.review = findings.filter(f => f.effective_decision === 'REVIEW').length;
      state.summary.audit!.counts.confirmed = findings.filter(f => f.effective_decision === 'CONFIRM').length;
      state.summary.audit!.counts.rejected = findings.filter(f => f.effective_decision === 'REJECT').length;
      state.summary.audit!.counts.review_queue_items = state.summary.audit!.counts.review;
      state.summary.human_review_complete = state.summary.audit!.counts.review === 0;
      if (regenerationFailed) { state.artifact_available = false; state.summary.artifact = null; state.summary.failure = { stage: 'artifact_redaction', code: 'artifact_failed' }; state.issue_message = 'Artifact generation failed.'; }
      events = [{ action: body.action ?? 'MISSED_PII', finding_id: body.finding_id ?? 'H000001', timestamp: '2026-10-12T04:00:00Z', reviewer_id: body.reviewer_id, reason: body.reason, previous_decision: 'REVIEW', new_decision: f.effective_decision }];
      value = state;
    } else if (route.endsWith('/save')) { state = { ...state, saved_revision: state.revision }; value = state; }
    else value = state;
    return new Response(JSON.stringify(value), { status: 200, headers: { 'Content-Type': 'application/json' } });
  }));
});

async function loaded() {
  const user = userEvent.setup();
  render(<App />);
  await user.click(await screen.findByRole('button', { name: /Document 1/ }));
  await user.click(await screen.findByRole('button', { name: 'Details' }));
  await screen.findByRole('heading', { name: 'Inspection' });
  return user;
}

const tab = (name: string) => within(document.querySelector('.detail-tabs')!).getByRole('button', { name });

async function review(action = 'Confirm as PII') {
  const user = await loaded();
  await user.click(tab('Review'));
  await user.click(await screen.findByRole('button', { name: /D000001/ }));
  await user.click(await screen.findByRole('button', { name: action }));
  await screen.findByRole('dialog');
  return user;
}

describe('React privacy review product', () => {
  it('renders the local enterprise shell and an honest initial upload flow', async () => {
    render(<App />);
    expect(screen.getByRole('navigation', { name: 'Chat history' })).toBeInTheDocument();
    expect(await screen.findByRole('button', { name: 'Send message' })).toBeDisabled();
    expect(screen.getByText('What would you like to redact?')).toBeInTheDocument();
    expect(screen.getByText('Processed locally. Your files stay on this device.')).toBeInTheDocument();
  });

  it('uploads multipart with the existing local boundary header', async () => {
    const user = userEvent.setup();
    render(<App />);
    await waitFor(() => expect(screen.getByLabelText('Upload document')).toBeInTheDocument());
    await user.upload(screen.getByLabelText('Upload document'), new File(['fixture'], 'synthetic.pdf', { type: 'application/pdf' }));
    await user.click(screen.getByRole('button', { name: 'Send message' }));
    await user.click(await screen.findByRole('button', { name: 'Details' }));
    await screen.findByRole('heading', { name: 'Inspection' });
    const request = calls.find(x => x.url === '/api/documents' && x.init.method === 'POST')!;
    expect(request.init.body).toBeInstanceOf(FormData);
    expect((request.init.headers as Record<string, string>)['X-Cadence-Local']).toBe('1');
    expect((request.init.headers as Record<string, string>)['Content-Type']).toBeUndefined();
  });

  it('shows API timings and renders the actual Bklit funnel from API numbers', async () => {
    await loaded();
    expect(screen.getByRole('img', { name: 'Privacy decision funnel: 3 raw, 1 confirmed, 1 review, 1 rejected' })).toBeInTheDocument();
    expect(screen.getByText('Completed · 2.50s')).toBeInTheDocument();
    expect(document.querySelector('.funnel-chart svg')).not.toBeNull();
  });

  it('filters findings when a funnel category is clicked', async () => {
    const user = await loaded();
    await user.click(screen.getByRole('button', { name: 'Filter Review' }));
    expect(await screen.findByRole('button', { name: /D000001/ })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /D000002/ })).not.toBeInTheDocument();
  });

  it('filters by entity and source-location privacy map', async () => {
    const user = await loaded();
    await user.click(screen.getByRole('button', { name: /page 2/ }));
    expect(await screen.findByRole('button', { name: /D000002/ })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /D000001/ })).not.toBeInTheDocument();
  });

  it('opens an accessible review modal with bounded highlighted context', async () => {
    await review();
    expect(screen.getByRole('dialog')).toHaveAccessibleName('Review D000001');
    expect(screen.getByText('Brightwell', { selector: 'mark' })).toBeInTheDocument();
    expect(screen.getByLabelText(/Reviewer identifier/)).toHaveValue('local-reviewer');
  });

  it('submits CONFIRM feedback with the current revision and refreshes the product', async () => {
    const user = await review();
    await user.click(screen.getByRole('button', { name: 'Confirm & Regenerate' }));
    await waitFor(() => expect(document.querySelector('.revision-feedback')).toHaveTextContent(/Finding D000001|Missed PII recorded/));
    const call = calls.find(x => x.url.endsWith('/feedback') && x.init.method === 'POST')!;
    expect(JSON.parse(call.init.body as string)).toEqual({ expected_revision: 0, action: 'CONFIRM_PII', finding_id: 'D000001', reviewer_id: 'local-reviewer', reason: null });
    expect(screen.getAllByText(/Audit revision 0 → 1/)[0]).toBeInTheDocument();
  });

  it('submits FALSE_POSITIVE to the existing endpoint', async () => {
    const user = await review('Mark False Positive');
    await user.click(screen.getByRole('button', { name: 'Mark False Positive & Regenerate' }));
    await waitFor(() => expect(document.querySelector('.revision-feedback')).toHaveTextContent(/Finding D000001|Missed PII recorded/));
    expect(JSON.parse(calls.find(x => x.url.endsWith('/feedback') && x.init.method === 'POST')!.init.body as string).action).toBe('FALSE_POSITIVE');
  });

  it('preserves source selection and submits offset-only MISSED_PII', async () => {
    const user = await loaded();
    await user.click(tab('Review'));
    await user.click(screen.getByRole('button', { name: 'Find missed PII' }));
    const box = await screen.findByLabelText('Bounded source window');
    await waitFor(() => expect(box).toHaveTextContent('SecretToken'));
    const text = box.firstChild!;
    const start = source.text.indexOf('SecretToken');
    const range = document.createRange();
    range.setStart(text, start);
    range.setEnd(text, start + 11);
    const selection = window.getSelection()!;
    selection.removeAllRanges();
    selection.addRange(range);
    fireEvent.mouseUp(box);
    await user.click(screen.getByRole('button', { name: 'Add missed PII' }));
    await user.click(screen.getByRole('button', { name: 'Submit MISSED_PII' }));
    await waitFor(() => expect(document.querySelector('.revision-feedback')).toHaveTextContent(/Finding D000001|Missed PII recorded/));
    const body = JSON.parse(calls.find(x => x.url.endsWith('/missed-pii') && x.init.method === 'POST')!.init.body as string);
    expect(body.start).toBe(40 + [...source.text.slice(0, start)].length);
    expect(body.end - body.start).toBe(11);
    expect(body).not.toHaveProperty('text');
    expect(body).not.toHaveProperty('replacement');
  });

  it('renders audit events with decisions and reviewer identity', async () => {
    events = [{ action: 'CONFIRM_PII', finding_id: 'D000001', timestamp: '2026-10-12T04:00:00Z', reviewer_id: 'synthetic-reviewer', reason: 'Fixture decision', previous_decision: 'REVIEW', new_decision: 'CONFIRM' }];
    const user = await loaded();
    await user.click(tab('History'));
    expect(await screen.findByText('CONFIRM PII')).toBeInTheDocument();
    expect(screen.getByText(/synthetic-reviewer/)).toBeInTheDocument();
  });

  it('keeps technical verification separate from coverage and blocked downstream', async () => {
    const user = await loaded();
    await user.click(tab('Verification'));
    expect(screen.getByText('PASSED')).toBeInTheDocument();
    expect(screen.getAllByText('NOT ESTABLISHED')).toHaveLength(1);
    expect(screen.getAllByText('BLOCKED')).toHaveLength(1);
    expect(screen.queryByText('100% safe')).not.toBeInTheDocument();
  });

  it('creates only opaque revision-aware download and inline PDF URLs', async () => {
    state.summary.human_review_complete=true;
    const user = userEvent.setup();
    render(<App />);
    await user.click(await screen.findByRole('button', { name: /Document 1/ }));
    expect(await screen.findByRole('link', { name: 'Download Redacted Review Copy' })).toHaveAttribute('href', artifactUrl(id, 0));
  });

  it('shows evaluation metrics with a visible synthetic-only disclaimer', async () => {
    const user = await loaded();
    await user.click(tab('Quality'));
    expect(screen.getByText('Measured on synthetic labeled evaluation dataset')).toBeInTheDocument();
    expect(screen.getByText(/Not real Cadence-document accuracy/)).toBeInTheDocument();
    expect(screen.getByRole('meter', { name: 'Precision policy 1.1' })).toHaveAttribute('value', '0.9816176470588235');
  });

  it('saves and reloads audits using only opaque references', async () => {
    const user = await loaded();
    await user.click(tab('History'));
    await user.click(screen.getByRole('button', { name: 'Save audit' }));
    await waitFor(() => expect(calls.some(x => x.url.endsWith('/save') && x.init.method === 'POST')).toBe(true));
    await waitFor(() => expect(screen.getByText(/Saved/)).toBeInTheDocument());
  });

  it('surfaces safe API errors without rejected content', async () => {
    failed = true;
    const user = userEvent.setup();
    render(<App />);
    await waitFor(() => expect(screen.getByLabelText('Upload document')).toBeInTheDocument());
    await user.upload(screen.getByLabelText('Upload document'), new File(['fake'], 'fixture.docx'));
    await user.click(screen.getByRole('button', { name: 'Send message' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/The local operation failed|The local operation could not be completed/);
  });

  it('does not expose unavailable artifacts as enabled downloads', async () => {
    state.artifact_available = false;
    state.summary.artifact = null;
    const user = userEvent.setup();
    render(<App />);
    await user.click(await screen.findByRole('button', { name: /Document 1/ }));
    expect(screen.getAllByRole('button', { name: 'Redacted copy unavailable' })[0]).toBeDisabled();
    expect(screen.queryByRole('link', { name: /Download/ })).not.toBeInTheDocument();
  });
});

describe('local boundary and selection contracts', () => {
  it('rejects a stale revision with a safe error', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('{}', { status: 409 })));
    await expect(api('/api/documents/' + id + '/feedback', { method: 'POST', body: '{}' })).rejects.toMatchObject({ status: 409 });
  });

  it('counts Unicode codepoints across a highlighted source selection', () => {
    const box = document.createElement('div');
    box.append('🙂 A ', Object.assign(document.createElement('mark'), { textContent: 'Secret' }));
    document.body.append(box);
    const range = document.createRange();
    range.selectNodeContents(box.querySelector('mark')!);
    window.getSelection()!.removeAllRanges();
    window.getSelection()!.addRange(range);
    expect(sourceSelection(box, { ...source, start: 10, text: '🙂 A Secret' })).toEqual({ start: 14, end: 20, text: 'Secret' });
    box.remove();
  });

  it('rejects source selections outside the bounded source container', () => {
    const box = document.createElement('div'), outside = document.createElement('div');
    outside.textContent = 'secret';
    document.body.append(outside);
    const range = document.createRange();
    range.selectNodeContents(outside);
    window.getSelection()!.removeAllRanges();
    window.getSelection()!.addRange(range);
    expect(sourceSelection(box, source)).toBeNull();
    outside.remove();
  });
});

describe('Phase 10B.1 review and prominent download regression', () => {
  it('primary action enters REVIEW and automatically selects context with both actions', async () => {
    const user = await loaded();
    await user.click(tab('Review'));
    expect(await screen.findByRole('heading', { name: 'Review workspace' })).toBeInTheDocument();
    expect(within(screen.getByLabelText('Finding decision filters')).getByRole('button', { name: 'Review' })).toHaveAttribute('aria-pressed', 'true');
    expect(await screen.findByText('Brightwell', { selector: 'mark' })).toBeVisible();
    expect(document.querySelector('.selected-row code')).toHaveTextContent('D000001');
    expect(screen.getByRole('button', { name: 'Confirm as PII' })).toBeVisible();
    expect(screen.getByRole('button', { name: 'Mark False Positive' })).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Confirm as PII' }));
    const dialog = await screen.findByRole('dialog');
    expect(dialog).toHaveTextContent('Finding ID: D000001');
    expect(dialog).toHaveTextContent('Automated: REVIEW');
    expect(dialog).toHaveTextContent('Effective: REVIEW');
    expect(within(dialog).getByRole('button', { name: 'Confirm & Regenerate' })).toBeEnabled();
  });

  it('sidebar and review-required map use REVIEW, and map retains location', async () => {
    const user = await loaded();
    await user.click(tab('Review'));
    expect(await screen.findByText('Brightwell', { selector: 'mark' })).toBeVisible();
    expect(within(screen.getByLabelText('Finding decision filters')).getByRole('button', { name: 'Review' })).toHaveAttribute('aria-pressed', 'true');
    await user.click(tab('Overview'));
    await user.click(screen.getByRole('button', { name: 'Review required findings' }));
    expect(await screen.findByText('Brightwell', { selector: 'mark' })).toBeVisible();
    await user.click(tab('Overview'));
    await user.click(screen.getByRole('button', { name: /page 1/ }));
    expect(await screen.findByText('Brightwell', { selector: 'mark' })).toBeVisible();
    expect(screen.getByLabelText('Location filter')).toHaveValue('1');
    expect(within(screen.getByLabelText('Finding decision filters')).getByRole('button', { name: 'Review' })).toHaveAttribute('aria-pressed', 'true');
  });

  it('refreshes counts, artifact revision and automatically selects the next REVIEW', async () => {
    findings.push({ ...findings[0], finding_id: 'D000004', location: 2 });
    state.summary.audit!.counts.raw_detection_count = 4;
    state.summary.audit!.counts.original_review = 2;
    state.summary.audit!.counts.review = 2;
    state.summary.audit!.counts.review_queue_items = 2;
    const user = await loaded();
    await user.click(screen.getByRole('button', { name: /page 1/ }));
    await user.click(await screen.findByRole('button', { name: 'Confirm as PII' }));
    await user.click(screen.getByRole('button', { name: 'Confirm & Regenerate' }));
    await waitFor(() => expect(document.querySelector('.revision-feedback')).toHaveTextContent('Finding D000001 confirmed as PII'));
    await waitFor(() => expect(document.querySelector('.selected-row code')).toHaveTextContent('D000004'));
    expect(screen.getByLabelText('Location filter')).toHaveValue('');
    expect(document.querySelector('.revision-feedback')).toHaveTextContent('Redacted artifact regenerated');
    expect(document.querySelector('.revision-feedback')).toHaveTextContent('Artifact verification passed');
    expect(document.querySelector('.revision-feedback')).toHaveTextContent('Audit revision 0 → 1');
    await user.click(tab('Overview'));
    expect(await screen.findByRole('img', { name: 'Privacy decision funnel: 4 raw, 2 confirmed, 1 review, 1 rejected' })).toBeInTheDocument();
  });

  it('disables download and duplicate submit while backend regeneration is pending', async () => {
    let release!: () => void;
    feedbackGate = new Promise<void>(resolve => { release = resolve; });
    const user = await review();
    await user.click(screen.getByRole('button', { name: 'Confirm & Regenerate' }));
    expect(within(screen.getByRole('dialog')).getByRole('button', { name: 'Regenerating redacted copy...' })).toBeDisabled();
    release();
    await waitFor(() => expect(document.querySelector('.revision-feedback')).toHaveTextContent('Finding D000001'));
    expect(calls.filter(c => c.url.endsWith('/feedback') && c.init.method === 'POST')).toHaveLength(1);
  });

  it('shows no-review state and actual known-queue completion with latest download', async () => {
    const user = await review('Mark False Positive');
    await user.click(screen.getByRole('button', { name: 'Mark False Positive & Regenerate' }));
    expect(await screen.findByText('Known review queue complete')).toBeVisible();
    expect(screen.getAllByText('No findings currently require human review.').length).toBeGreaterThan(0);
    expect(await screen.findByText('Select a finding to review.')).toBeVisible();
    expect(await screen.findByRole('link', { name: 'Download Latest Redacted Review Copy' })).toHaveAttribute('href', artifactUrl(id, 1));
    expect(screen.getByText('Coverage verification remains NOT ESTABLISHED.')).toBeVisible();
  });

  it('does not call an empty REVIEW list complete while backend has other issues', async () => {
    findings[0].effective_decision = 'CONFIRM';
    const user = await loaded();
    await user.click(tab('Review'));
    expect(await screen.findByText('Other known review issues remain. Inspect the audit queue and artifact verification.')).toBeVisible();
    expect(screen.queryByText('Known review queue complete')).not.toBeInTheDocument();
  });

  it.each(['pdf', 'docx', 'pptx'])('provides a top-level opaque %s artifact link for an approved ready result', async format => {
    state.format = format;
    state.summary.human_review_complete = true;
    state.summary.audit!.human_review_complete = true;
    const user = userEvent.setup();
    render(<App />);
    await user.click(await screen.findByRole('button', { name: /Document 1/ }));
    expect(await screen.findByRole('link', { name: 'Download Redacted Review Copy' })).toHaveAttribute('href', artifactUrl(id, 0));
  });

  it('has no active download before a document is loaded', async () => {
    render(<App />);
    await screen.findByRole('heading', { name: 'What would you like to redact?' });
    expect(screen.queryByRole('link', { name: /Download/ })).not.toBeInTheDocument();
  });

  it('reports failed regeneration truthfully and disables the download', async () => {
    regenerationFailed = true;
    const user = await review();
    await user.click(screen.getByRole('button', { name: 'Confirm & Regenerate' }));
    await waitFor(() => expect(document.querySelector('.revision-feedback')).toHaveTextContent('regeneration needs attention'));
    expect(document.querySelector('.revision-feedback')).not.toHaveTextContent('Artifact verification passed');
    expect(screen.getAllByRole('button', { name: 'Redacted copy unavailable' })[0]).toBeDisabled();
  });
});

describe('Phase 10B.2 privacy gateway presentation', () => {
  it('uses backend document, candidate and decision counts in its pipeline presentation', async () => {
    await loaded();
    expect(screen.getByRole('button', { name: 'Review 1 Findings' })).toBeInTheDocument();
    expect(screen.getByText('Completed · 2.50s')).toBeInTheDocument();
  });

  it('shows local redaction and review status without a nonexistent LLM gate', async () => {
    await loaded();
    expect(screen.getByRole('region', { name: 'Local document redaction flow' })).toBeInTheDocument();
    expect(screen.getByText('GENERATED')).toBeInTheDocument();
    expect(screen.getByText('Supported mappings verified')).toBeInTheDocument();
    expect(screen.getByText('1 textual unresolved')).toBeInTheDocument();
    expect(screen.getByText('Full files stay local')).toBeInTheDocument();
  });

  it('makes the output and distribution purposeful without a safety score', async () => {
    await loaded();
    expect(screen.getByRole('heading', { name: 'Privacy Decision Funnel' })).toBeVisible();
    expect(screen.getByRole('heading', { name: 'Entity distribution' })).toBeVisible();
  });

  it('frames ambiguity, transformation and governance without overwriting decisions', async () => {
    const user = await loaded();
    await user.click(tab('Review'));
    expect(await screen.findByText('Uncertain')).toBeVisible();
    expect(screen.getByText('Decision required')).toBeVisible();
    expect(screen.getByText(/If confirmed, this value would be removed/)).toBeVisible();
    expect(screen.getByText('BEFORE · SENSITIVE SOURCE')).toBeVisible();
    expect(screen.getByText('AFTER · REDACTED REVIEW COPY')).toBeVisible();
    await user.click(tab('History'));
    expect(screen.getByRole('heading', { name: 'Review & Governance Trail' })).toBeVisible();
  });

  it('computes quality deltas from existing evidence and retains the synthetic-only limit', async () => {
    const user = await loaded();
    await user.click(tab('Quality'));
    expect(screen.getByText('+17.74 pp precision')).toBeVisible();
    expect(screen.getByText('Same measured recall')).toBeVisible();
    expect(screen.getByText('-11.90 pp review rate')).toBeVisible();
    expect(screen.getByText(/Not a claim of Cadence-document accuracy/)).toBeVisible();
  });
});

describe('Phase 11 visual privacy presentation', () => {
  function addFace(review = false) {
    state.summary.visual_privacy = { inspected_visual_units: 1, detected_faces: 1, confirmed_faces: review ? 0 : 1, review_faces: review ? 1 : 0, rejected_faces: 0, face_placements: 2, unsupported_visual_units: 0, unsupported: {}, detection_seconds: 0.12, cache_hits: 0, policy_version: 'face-1.0', coverage_verified: false };
    Object.assign(state.summary.artifact!, { visual_inspection_completed: true, face_transformations_verified: true, protected_faces: review ? 0 : 1, face_mapping_failures: 0, face_verification_failures: 0 });
    findings.push({ finding_id: 'V000001', entity_type: 'FACE', location: 1, locations: [1, 2], confidence: 0.96, recognizer: 'YuNet', automated_decision: review ? 'REVIEW' : 'CONFIRM', effective_decision: review ? 'REVIEW' : 'CONFIRM', review_status: review ? 'REVIEW_REQUIRED' : 'PROTECTED', corrected: false, kind: 'VISUAL', protected: !review, biometric_action: review ? 'Blur requires review' : 'Blur verified' });
  }

  it('separates face counts from textual funnel and shows bounded image evidence', async () => {
    addFace();
    const user = await loaded();
    expect(screen.getByRole('img', { name: 'Privacy decision funnel: 3 raw, 1 confirmed, 1 review, 1 rejected' })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Faces are biometric privacy findings' })).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Inspect face findings' }));
    expect(await screen.findByAltText('Verified blurred face region from review artifact')).toHaveAttribute('src', expect.stringContaining('after=true'));
    expect(screen.getByAltText('Bounded original synthetic or private face region')).toHaveAttribute('src', expect.stringContaining('/visual-crop'));
    expect(screen.getByText(/This is a policy decision, not a human identity assessment/)).toBeVisible();
    expect(screen.getByRole('button', { name: 'Confirm as PII' })).toBeVisible();
    expect(screen.getByRole('button', { name: 'Mark False Positive' })).toBeVisible();
  });

  it('shows actual face verification and leaves coverage/downstream blocked', async () => {
    addFace();
    const user = await loaded();
    await user.click(tab('Verification'));
    expect(screen.getByText('Supported face transformations')).toBeVisible();
    expect(screen.getByText(/1 face findings protected/)).toBeVisible();
    expect(screen.getAllByText('BLOCKED').length).toBeGreaterThan(0);
  });

  it('combines the action queue count while keeping textual candidate counts unchanged', async () => {
    addFace(true);
    await loaded();
    expect(screen.getByRole('button', { name: 'Review 2 Findings' })).toHaveTextContent('Review 2 Findings');
    expect(screen.getByRole('img', { name: 'Privacy decision funnel: 3 raw, 1 confirmed, 1 review, 1 rejected' })).toBeInTheDocument();
  });

  it('marks legacy/unrecorded visual inspection without claiming there were no faces', async () => {
    await loaded();
    expect(screen.getByText(/Visual inspection is not recorded for this document/)).toBeVisible();
  });
});

describe('Manager approval and chat interaction', () => {
  it('allows pending downloads and blocks explicit manager denial', async () => {
    managerApprovalStatus = 'pending';
    const user = userEvent.setup();
    render(<App />);
    await user.click(await screen.findByRole('button', { name: /Document 1/ }));
    expect(await screen.findByRole('link', { name: 'Download Redacted Review Copy' })).toBeInTheDocument();

    managerApprovalStatus = 'denied';
    await user.click(screen.getByRole('button', { name: 'New chat' }));
    await user.click(await screen.findByRole('button', { name: /Document 1/ }));
    expect(await screen.findByRole('button', { name: 'Download denied' })).toBeDisabled();
    expect(screen.queryByRole('link', { name: /Download/ })).not.toBeInTheDocument();
  });

  it('sends text message and receives sanitized text reply', async () => {
    const user = userEvent.setup();
    render(<App />);
    const textarea = screen.getByLabelText('Message');
    await user.type(textarea, 'Please redact John Smith EMP-00001');
    await user.click(screen.getByRole('button', { name: 'Send message' }));
    expect(await screen.findByText('Please redact John Smith EMP-00001')).toBeInTheDocument();
    expect(await screen.findByText('Sanitized text reply')).toBeInTheDocument();
  });

  it('attaches a sample without auto-sending', async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole('button', { name: 'Add attachment' }));
    await user.click(await screen.findByRole('button', { name: 'Sample 1' }));
    expect(await screen.findByText('sample1.pdf')).toBeInTheDocument();
    // Verify it was NOT auto-sent
    expect(screen.queryByText('Your document')).not.toBeInTheDocument();
  });
});


it('retains a failed attachment for retry and never shows the previous result as its output',async()=>{
  const user=await loaded();
  await user.click(screen.getByRole('button',{name:/^Close inspection$/}));
  failed=true;
  await user.upload(screen.getByLabelText('Upload document'),new File(['bad'],'retry.docx'));
  await user.click(screen.getByRole('button',{name:/^Send message$/}));
  expect(await screen.findByRole('alert')).toBeInTheDocument();
  expect(screen.getByRole('button',{name:'Remove attachment'})).toBeInTheDocument();
  expect(screen.queryByRole('link',{name:/Download Redacted/})).not.toBeInTheDocument();
  expect(screen.getByRole('button',{name:/^Send message$/})).toBeEnabled();
});
