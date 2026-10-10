import type { InputHTMLAttributes, ReactNode } from "react";

export function FormField({
  label,
  error,
  id,
  children,
}: {
  label: string;
  error?: string;
  id: string;
  children?: ReactNode;
} & InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label htmlFor={id}>
      {label}
      {children ?? (
        <input id={id} aria-invalid={Boolean(error)} aria-describedby={error ? `${id}-error` : undefined} />
      )}
      {error && <small id={`${id}-error`} role="alert">{error}</small>}
    </label>
  );
}
