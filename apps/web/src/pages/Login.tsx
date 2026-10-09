import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../features/auth/useAuth";
import { api } from "../lib/api";
import { loginInput, session } from "../lib/schemas";

export default function Login() {
  const { identity, loading, error, reload } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [loginError, setLoginError] = useState("");
  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoginError("");
    const parsed = loginInput.safeParse({ email, password });
    if (!parsed.success) {
      setLoginError("Enter a valid email and a password of 12–128 characters.");
      return;
    }
    setSubmitting(true);
    try {
      const signedIn = await api("/auth/login", session, {
        method: "POST",
        body: JSON.stringify(parsed.data),
      });
      setPassword("");
      await reload();
      navigate(signedIn.user.role === "manager" ? "/company/setup" : "/chat", {
        replace: true,
      });
    } catch (e) {
      setLoginError(e instanceof Error ? e.message : "Could not sign in");
    } finally {
      setSubmitting(false);
    }
  }
  if (loading) return <p role="status">Loading…</p>;
  if (identity)
    return (
      <Navigate
        to={identity.user.role === "manager" ? "/company/setup" : "/chat"}
        replace
      />
    );
  return (
    <section>
      <h1>PII Guard</h1>
      <p>Sign in with your company account.</p>
      {(loginError || error) && <p role="alert">{loginError || error}</p>}
      <form onSubmit={submit}>
        <label>
          Email
          <input
            type="email"
            autoComplete="username"
            required
            maxLength={254}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>
        <label>
          Password
          <input
            type="password"
            autoComplete="current-password"
            required
            minLength={12}
            maxLength={128}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        <button type="submit" disabled={submitting}>
          {submitting ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </section>
  );
}
