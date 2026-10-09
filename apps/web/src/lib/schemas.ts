import { z } from "zod";
const id = z.uuid();
export const role = z.enum(["employee", "manager"]);
export const userSummary = z.strictObject({
  id,
  email: z.string(),
  display_name: z.string().min(1).max(120),
  role,
});
export const organization = z.strictObject({
  id,
  name: z.string().min(1).max(120),
  created_at: z.iso.datetime(),
});
export const session = z.strictObject({
  user: userSummary.extend({ organization_id: id }),
  organization: z.strictObject({ id, name: z.string().min(1).max(120) }),
  csrf_token: z.string().min(1),
});
export const organizationInput = z.strictObject({
  name: z.string().trim().min(1).max(120),
});
export const assignmentInput = z.strictObject({ manager_id: id });
export const loginInput = z.strictObject({
  email: z.string(),
  password: z.string(),
});
export const signupInput = loginInput.extend({
  display_name: z.string().min(1).max(120),
});
export const assignment = z.strictObject({
  employee_id: id,
  manager_id: id,
  updated_at: z.iso.datetime(),
});
export const usersPage = z.strictObject({
  items: z.array(userSummary),
  next_cursor: z.string().nullable(),
});
export const assignmentsPage = z.strictObject({
  items: z.array(assignment),
  next_cursor: z.string().nullable(),
});
export const apiError = z.strictObject({
  error: z.strictObject({
    code: z.string(),
    message: z.string(),
    fields: z.array(z.strictObject({ path: z.string(), message: z.string() })),
    request_id: id,
  }),
});

const timestamp = z.iso.datetime({ offset: true });
const pageCursor = z.string().max(512).nullable();
export const attachment = z.strictObject({
  id,
  filename: z.string().min(1).max(255),
  mime_type: z.enum([
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "image/png",
    "image/jpeg",
  ]),
  size_bytes: z.number().int().min(1).max(25 * 1024 * 1024),
  state: z.enum(["pending_upload", "uploaded", "processing", "sanitized", "failed"]),
  sanitized_download_url: z.string().nullable(),
});
export const uploadGrant = z.strictObject({
  method: z.literal("PUT"),
  url: z.string().url(),
  headers: z.record(z.string(), z.string()),
  expires_at: timestamp,
});
export const uploadInitResponse = z.strictObject({
  attachment,
  upload: uploadGrant,
});
export const conversation = z.strictObject({
  id,
  title: z.string().min(1).max(120),
  created_at: timestamp,
  updated_at: timestamp,
});
export const message = z.strictObject({
  id,
  conversation_id: id,
  role: z.enum(["user", "assistant"]),
  text: z.string().max(100_000),
  attachment_ids: z.array(id).max(5),
  state: z.enum(["processing", "completed", "failed", "cancelled"]),
  created_at: timestamp,
});
export const conversationsPage = z.strictObject({
  items: z.array(conversation),
  next_cursor: pageCursor,
});
export const messagesPage = z.strictObject({
  items: z.array(message),
  next_cursor: pageCursor,
});
export const demoSample = z.discriminatedUnion("kind", [
  z.strictObject({
    id,
    kind: z.literal("message"),
    title: z.string().min(1).max(80),
    description: z.string().min(1).max(240),
    tags: z.array(z.enum(["text_pii", "scanned_text", "faces", "custom_rules"])).max(4),
    text: z.string().min(1).max(100_000),
  }),
  z.strictObject({
    id,
    kind: z.literal("file"),
    title: z.string().min(1).max(80),
    description: z.string().min(1).max(240),
    tags: z.array(z.enum(["text_pii", "scanned_text", "faces", "custom_rules"])).max(4),
    filename: z.string().min(1).max(255),
    mime_type: attachment.shape.mime_type,
    size_bytes: z.number().int().min(1).max(25 * 1024 * 1024),
  }),
]);
export const demoSamplesResponse = z.strictObject({ items: z.array(demoSample) });
export const processingEvent = z.strictObject({
  type: z.literal("processing"),
  submission_id: id,
  stage: z.literal("sanitizing"),
});
export const sanitizedEvent = z.strictObject({
  type: z.literal("sanitized"),
  submission_id: id,
  user_message: message,
  attachments: z.array(attachment),
  policy_version: z.string().min(1),
});
export const deltaEvent = z.strictObject({
  type: z.literal("delta"),
  submission_id: id,
  assistant_message_id: id,
  sequence: z.number().int().positive(),
  text: z.string(),
});
export const doneEvent = z.strictObject({
  type: z.literal("done"),
  submission_id: id,
  assistant_message: message,
});
export const errorEvent = z.strictObject({
  type: z.literal("error"),
  submission_id: id,
  code: z.string(),
  message: z.string(),
  retryable: z.boolean(),
});
export const streamEvent = z.discriminatedUnion("type", [
  processingEvent,
  sanitizedEvent,
  deltaEvent,
  doneEvent,
  errorEvent,
]);
export type Session = z.infer<typeof session>;
export type Attachment = z.infer<typeof attachment>;
export type Conversation = z.infer<typeof conversation>;
export type DemoSample = z.infer<typeof demoSample>;
export type Message = z.infer<typeof message>;
export type StreamEvent = z.infer<typeof streamEvent>;
