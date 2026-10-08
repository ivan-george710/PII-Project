import { useState } from "react";
import { z } from "zod";
import { usersPage, assignmentsPage } from "../../lib/schemas";
export function EmployeeAssignments({
  users,
  assignments,
  save,
}: {
  users: z.infer<typeof usersPage>["items"];
  assignments: z.infer<typeof assignmentsPage>["items"];
  save: (employee: string, manager: string) => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const managers = users.filter((u) => u.role === "manager");
  return (
    <section>
      <h2>Employee managers</h2>
      {error && <p role="alert">{error}</p>}
      {users
        .filter((u) => u.role === "employee")
        .map((employee) => {
          const current =
            assignments.find((a) => a.employee_id === employee.id)
              ?.manager_id ?? "";
          return (
            <div className="assignment" key={employee.id}>
              <label htmlFor={employee.id}>
                {employee.display_name}
                <small>{employee.email}</small>
              </label>
              <select
                id={employee.id}
                disabled={busy}
                value={current}
                onChange={async (e) => {
                  setBusy(true);
                  setError("");
                  try {
                    await save(employee.id, e.target.value);
                  } catch (e) {
                    setError(e instanceof Error ? e.message : "Could not save");
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                <option value="">Unassigned</option>
                {managers.map((manager) => (
                  <option key={manager.id} value={manager.id}>
                    {manager.display_name}
                  </option>
                ))}
              </select>
            </div>
          );
        })}
      {!users.some((u) => u.role === "employee") && (
        <p>No employees have been provisioned.</p>
      )}
    </section>
  );
}
