export const codePointLength = text => [...text].length;
export const codePointSlice = (text, start, end) => [...text].slice(start, end).join('');
export function sourceSelection(prefix, selected, windowStart) {
  const start = windowStart + codePointLength(prefix);
  const end = start + codePointLength(selected);
  if (end <= start || end - start > 1000) throw new Error('Select between 1 and 1,000 source characters.');
  return {start, end};
}
export function feedbackPayload(revision, findingId, action, reviewer, reason) {
  return {expected_revision: revision, finding_id: findingId, action, reviewer_id: reviewer, reason: reason || null};
}
export function missedPayload(revision, location, range, entity, reviewer, reason) {
  return {expected_revision: revision, location, start: range.start, end: range.end,
    entity_type: entity, reviewer_id: reviewer, reason: reason || null};
}
export function stageLabel(name) {
  return ({file_intelligence:'File intelligence', extraction:'Extraction', detection:'PII detection',
    redaction:'Text redaction', audit:'Audit', artifact_redaction:'Artifact redaction',
    artifact_verification:'Artifact verification'})[name] || name;
}
