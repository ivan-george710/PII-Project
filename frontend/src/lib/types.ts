export type Decision = 'ALL' | 'CONFIRM' | 'REVIEW' | 'REJECT';
export interface Stage { name: string; state: 'Pending' | 'Completed' | 'Failed'; seconds: number | null }
export interface Counts { raw_detection_count:number; original_confirmed:number; original_review:number; original_rejected:number; confirmed:number; review:number; rejected:number; human_added:number; applied_redactions:number; review_queue_items:number; feedback_events:number; [key:string]:number }
export interface Artifact { format:string|null; redaction_completed:boolean; verification_completed:boolean; reopened:boolean; supported_content_verified:boolean; artifact_verified:boolean; mapping_failures:number; verification_failures:number; residual_confirmed_values:number; residual_sensitive_patterns:number; unsupported_structures:Record<string,number>; applied_redactions:number; page_count_preserved:boolean; safe_for_llm:false; coverage_verified:false; downstream_export_permitted:false;visual_inspection_completed?:boolean;face_transformations_verified?:boolean;protected_faces?:number;face_mapping_failures?:number;face_verification_failures?:number;unsupported_visual_content?:Record<string,number> }
export interface VisualInspection { inspected_visual_units:number;detected_faces:number;confirmed_faces:number;review_faces:number;rejected_faces:number;face_placements:number;unsupported_visual_units:number;unsupported:Record<string,number>;detection_seconds:number;cache_hits:number;policy_version:string;coverage_verified:false }
export interface Summary { visual_privacy?:VisualInspection|null; processing_status:string; coverage_status:string; coverage_verified:false; safe_for_llm:false; downstream_export_permitted:false; total_runtime_seconds:number; failure:{stage:string;code:string}|null; human_review_complete:boolean; extraction_completed:boolean; detection_completed:boolean; text_redaction_completed:boolean; artifact:Artifact|null; audit:{counts:Counts;revision:number;human_review_complete:boolean;redaction_complete:boolean}|null }
export interface DocumentState { manager_approval?:'pending'|'approved'|'denied'; input_text?:string|null;output_text?:string|null; document_session_id:string; format:string; revision:number|null; saved_revision:number|null; artifact_available:boolean; summary:Summary; stages:Stage[]; issue_message:string|null }
export interface Identity { display_name:string; location_kind:string; location_count:number }
export interface Finding { finding_id:string; entity_type:string; location:number; confidence:number; recognizer:string; automated_decision:string|null; effective_decision:string; review_status:string; corrected:boolean;kind?:'TEXT'|'VISUAL';locations?:number[];biometric_action?:string|null;protected?:boolean;visual_location_label?:string|null }
export interface FindingList { items:Finding[]; total:number; entities:string[]; locations:number[] }
export interface Detail { finding:Finding; before:string;candidate:string;after:string;candidate_truncated:boolean;visual_before_url?:string|null;visual_after_url?:string|null }
export interface Comparison { finding_id:string; redacted_context:string|null; replacement:string|null; state:string }
export interface SourceWindow { location:number;start:number;total_characters:number;text:string;highlights:{finding_id:string;start:number;end:number;decision:string}[] }
export interface AuditEvent { action:string;finding_id:string;timestamp:string;reviewer_id:string;reason:string|null;previous_decision:string|null;new_decision:string }
export interface AuditView { summary:Summary;events:AuditEvent[] }
export interface SavedAudit { audit_reference:string;label:string }
export interface Config { manager_url?:string; max_upload_bytes:number; supported_formats:string[];trusted_local_only:boolean }
export interface RangeSelection { start:number;end:number;text:string }
export type Screen = 'Overview'|'Documents'|'Review Queue'|'Audit'|'Detector Quality'|'Artifact Verification';

export interface ManagerPart { finding_id:string;category:string;original:string;redacted:string|null;original_image?:string|null;redacted_image?:string|null;truncated:boolean }
export interface ManagerReport { id:string;filename:string;revision:number;artifact_sha256:string|null;ready:boolean;parts?:ManagerPart[];counts:Record<string,number>;status:'pending'|'approved'|'denied';submitted_at:string;decided_at:string|null }
export interface CustomRule { id:string;name:string;pattern:string;entity_type:string;action:'redact'|'block';is_regex:boolean;created_at?:string }

export interface PreviewPageItem { page_number:number; kind:string; original_text:string; redacted_text:string; extraction_method:string }
export interface PreviewPagesResponse { format:string; filename:string; location_kind:string; total_pages:number; pages:PreviewPageItem[]; redactions:{tag:string;entity_type:string;original_text:string;page_number:number}[] }
