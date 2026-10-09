import { z } from "zod";
const id = z.uuid();
export const role = z.enum(["employee", "manager"]);
export const userSummary = z.strictObject({
  id,
  email: z.email(),
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
export type Session = z.infer<typeof session>;
export const loginInput = z.strictObject({
  email: z
    .email()
    .max(254)
    .transform((value) => value.toLowerCase()),
  password: z.string().min(12).max(128),
});
