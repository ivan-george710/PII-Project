import { render, screen } from '@testing-library/react';
import { beforeEach, expect, it, vi } from 'vitest';
import { ChatDocument } from '../components/chat-document';
import { DocumentPreview } from '../components/document-preview';
import { InspectionPage } from '../components/inspection-page';
import type { DocumentState, Identity, PreviewPagesResponse } from '../lib/types';

const mockState: DocumentState = {
  document_session_id: 'c'.repeat(32),
  format: 'pptx',
  revision: 1,
  saved_revision: null,
  artifact_available: true,
  summary: {
    processing_status: 'complete',
    coverage_status: 'unverified',
    coverage_verified: false,
    safe_for_llm: false,
    downstream_export_permitted: false,
    total_runtime_seconds: 1.2,
    failure: null,
    human_review_complete: true,
    extraction_completed: true,
    detection_completed: true,
    text_redaction_completed: true,
    artifact: {
      format: 'pptx',
      redaction_completed: true,
      verification_completed: true,
      reopened: false,
      supported_content_verified: true,
      artifact_verified: true,
      mapping_failures: 0,
      verification_failures: 0,
      residual_confirmed_values: 0,
      residual_sensitive_patterns: 0,
      unsupported_structures: {},
      applied_redactions: 5,
      page_count_preserved: true,
      safe_for_llm: false,
      coverage_verified: false,
      downstream_export_permitted: false
    },
    audit: null
  },
  stages: [],
  issue_message: null
};

const mockIdentity: Identity = {
  display_name: 'test_presentation.pptx',
  location_kind: 'slide',
  location_count: 3
};

const mockPreviewPages: PreviewPagesResponse = {
  format: 'pptx',
  filename: 'test_presentation.pptx',
  location_kind: 'slide',
  total_pages: 3,
  pages: [
    {
      page_number: 1,
      kind: 'slide',
      original_text: 'Slide 1: Cadence TPRM\nExecutive summary by Desmond Achterberg',
      redacted_text: 'Slide 1: [CUSTOM_BLOCKED_001]\nExecutive summary by [PERSON_001]',
      extraction_method: 'native'
    },
    {
      page_number: 2,
      kind: 'slide',
      original_text: 'Slide 2: Optiv Security and OneTrust TPRM integration',
      redacted_text: 'Slide 2: [CUSTOM_BLOCKED_002] Security and [CUSTOM_BLOCKED_003] integration',
      extraction_method: 'native'
    }
  ],
  redactions: [
    { tag: '[CUSTOM_BLOCKED_001]', entity_type: 'CUSTOM_BLOCKED', original_text: 'Cadence TPRM', page_number: 1 },
    { tag: '[PERSON_001]', entity_type: 'PERSON', original_text: 'Desmond Achterberg', page_number: 1 },
    { tag: '[CUSTOM_BLOCKED_002]', entity_type: 'CUSTOM_BLOCKED', original_text: 'Optiv', page_number: 2 }
  ]
};

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn(async (input: string) => {
    const url = String(input);
    if (url.includes('/preview-pages')) {
      return new Response(JSON.stringify(mockPreviewPages), { status: 200, headers: { 'content-type': 'application/json' } });
    }
    if (url.includes('/review')) {
      return new Response(JSON.stringify(mockIdentity), { status: 200, headers: { 'content-type': 'application/json' } });
    }
    if (url.includes('/findings')) {
      return new Response(JSON.stringify({ items: [] }), { status: 200, headers: { 'content-type': 'application/json' } });
    }
    if (url.includes('/audit')) {
      return new Response(JSON.stringify({ summary: mockState.summary, events: [] }), { status: 200, headers: { 'content-type': 'application/json' } });
    }
    return new Response(JSON.stringify(mockState), { status: 200, headers: { 'content-type': 'application/json' } });
  }));
});

it('renders DocumentPreview with slides, pills and redaction summary', async () => {
  const onClose = vi.fn();
  render(<DocumentPreview mode="redacted" state={mockState} identity={mockIdentity} onClose={onClose} />);

  expect(await screen.findByText('test_presentation.pptx')).toBeInTheDocument();
  expect(await screen.findByText(/Slide 1 of 3/)).toBeInTheDocument();
  expect(await screen.findByText('[CUSTOM_BLOCKED_001]')).toBeInTheDocument();
  expect(screen.getByText('[PERSON_001]')).toBeInTheDocument();
  expect(screen.getByText('3 PII Replacements Applied')).toBeInTheDocument();
});

it('renders InspectionPage with full tabs, hero card, and back link', async () => {
  render(<InspectionPage documentId={'c'.repeat(32)} />);

  expect(await screen.findByText('Back to Chat')).toBeInTheDocument();
  expect(screen.getByText('Document Inspection')).toBeInTheDocument();
  expect(await screen.findByText('Overview & Pipeline')).toBeInTheDocument();
  expect(screen.getByText('Audit History')).toBeInTheDocument();
  expect(screen.getByText('Artifact Verification')).toBeInTheDocument();
});

for(const format of ['pdf','image','docx','pptx'])it(`shows a returned ${format} preview without exposing original text`,async()=>{
 render(<ChatDocument state={{...mockState,format}} mode="redacted" name="sample" label="Redacted" onOpen={()=>{}}/>);
 if(['pdf','image'].includes(format)){expect(screen.getByAltText('redacted sample preview')).toHaveAttribute('src',expect.stringContaining('variant=redacted'));}
 else{expect(await screen.findByText(/Executive summary by \[PERSON_001\]/)).toBeInTheDocument();expect(screen.queryByText(/Desmond Achterberg/)).not.toBeInTheDocument();}
});
it('does not fetch or display a denied returned preview',()=>{
 render(<ChatDocument state={mockState} mode="redacted" name="sample" label="Denied" disabled onOpen={()=>{}}/>);
 expect(screen.getByRole('button')).toBeDisabled();expect(fetch).not.toHaveBeenCalled();expect(screen.queryByRole('img')).not.toBeInTheDocument();
});
