import { z } from "zod";
import { apiError } from "./schemas";
export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
export async function api<T>(
  path: string,
  schema: z.ZodType<T>,
  options: RequestInit = {},
  csrf?: string,
): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...options,
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      ...(csrf ? { "X-CSRF-Token": csrf } : {}),
      ...options.headers,
    },
  });
  if (!response.ok) {
    const body = apiError.safeParse(await response.json().catch(() => null));
    throw new ApiError(
      response.status,
      body.success ? body.data.error.message : "Request failed",
    );
  }
  return schema.parse(
    response.status === 204 ? undefined : await response.json(),
  );
}
