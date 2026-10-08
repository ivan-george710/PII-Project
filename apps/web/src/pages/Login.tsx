import { Navigate } from "react-router-dom";
import { useAuth } from "../features/auth/useAuth";
export default function Login() {
  const { identity, loading, error } = useAuth();
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
      {error && <p role="alert">{error}</p>}
      <a className="button" href="/api/v1/auth/login">
        Sign in
      </a>
    </section>
  );
}
