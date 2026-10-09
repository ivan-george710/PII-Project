import { useState, type FormEvent } from "react";
import { z } from "zod";
import { employeeInput, employeeCreated, usersPage } from "../../lib/schemas";
import { LoadingIndicator } from "../../components/LoadingIndicator";
export function AddEmployeeForm({
  managers,
  currentManager,
  save,
}: {
  managers: z.infer<typeof usersPage>["items"];
  currentManager: string;
  save: (
    input: z.input<typeof employeeInput>,
  ) => Promise<z.infer<typeof employeeCreated>>;
}) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [manager, setManager] = useState(currentManager);
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  async function submit(e: FormEvent) {
    e.preventDefault();
    if (busy) return;
    setError("");
    setSuccess("");
    const parsed = employeeInput.safeParse({
      display_name: name,
      email,
      password,
      manager_id: manager,
    });
    if (!parsed.success) {
      setError("Enter a name and choose an immediate manager.");
      return;
    }
    setBusy(true);
    try {
      const result = await save(parsed.data);
      setSuccess(
        `${result.user.display_name} can now sign in with the email and password you entered.`,
      );
      setName("");
      setEmail("");
      setPassword("");
      setShow(false);
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Could not add employee. Try again.",
      );
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="settings-section" aria-labelledby="add-employee-title">
      <div className="section-heading">
        <h2 id="add-employee-title">Add an employee</h2>
        <p>
          Create their account in this workspace. Share the sign-in details with
          them directly.
        </p>
      </div>
      <form
        className="employee-form"
        onSubmit={submit}
        noValidate
        aria-busy={busy}
      >
        <div className="field">
          <label htmlFor="employee-name">Full name</label>
          <input
            id="employee-name"
            autoComplete="off"
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={120}
            placeholder="Jordan Lee"
          />
        </div>
        <div className="field">
          <label htmlFor="employee-email">Employee email</label>
          <input
            id="employee-email"
            type="text"
            inputMode="email"
            autoComplete="off"
            autoCapitalize="none"
            spellCheck={false}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="jordan@company.com"
          />
        </div>
        <div className="field">
          <label htmlFor="employee-password">Password</label>
          <div className="password-field">
            <input
              id="employee-password"
              type={show ? "text" : "password"}
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Set their sign-in password"
            />
            <button
              className="quiet-button password-reveal"
              type="button"
              onClick={() => setShow(!show)}
              aria-pressed={show}
            >
              {show ? "Hide" : "Show"}
            </button>
          </div>
        </div>
        <div className="field">
          <label htmlFor="employee-manager">Immediate manager</label>
          <select
            id="employee-manager"
            value={manager}
            onChange={(e) => setManager(e.target.value)}
          >
            {managers.map((m) => (
              <option key={m.id} value={m.id}>
                {m.display_name}
                {m.id === currentManager ? " (you)" : ""}
              </option>
            ))}
          </select>
        </div>
        {error && (
          <p role="alert" className="form-error">
            {error}
          </p>
        )}
        {success && (
          <p role="status" className="form-success">
            {success}
          </p>
        )}
        <div className="form-actions">
          <button className="primary-button" disabled={busy} type="submit">
            {busy ? "Adding employee…" : "Add employee"}
          </button>
          <span>No invitation email is sent.</span>
          {busy && <LoadingIndicator label="Creating account…" />}
        </div>
      </form>
    </section>
  );
}
