export function StatusMessage({
  children,
  state = "status",
}: {
  children: string;
  state?: "status" | "alert";
}) {
  return <p role={state}>{children}</p>;
}
