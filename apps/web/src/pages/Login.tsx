import { BrandMark } from "../components/BrandMark";
import { ThemeToggle } from "../components/ThemeToggle";
import { LoadingIndicator } from "../components/LoadingIndicator";
import { useState, type FormEvent } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../features/auth/useAuth";
import { api } from "../lib/api";
import { loginInput, signupInput, session } from "../lib/schemas";

export default function Login() {
  const { identity, loading, error, reload } = useAuth();
  const navigate = useNavigate();
  const signup = useLocation().pathname === "/signup";
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [loginError, setLoginError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (submitting) return;
    setLoginError("");
    const body = signup
      ? signupInput.parse({ email, password, display_name: name })
      : loginInput.parse({ email, password });
    setSubmitting(true);
    try {
      const signedIn = await api(
        signup ? "/auth/signup" : "/auth/login",
        session,
        {
          method: "POST",
          body: JSON.stringify(body),
        },
      );
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

  if (identity)
    return (
      <Navigate
        to={identity.user.role === "manager" ? "/company/setup" : "/chat"}
        replace
      />
    );
  return (
    <div className="auth-page">
      <div className="auth-brand">
        <span className="brand-lockup">
          <BrandMark />
          PII Guard
        </span>
        <ThemeToggle />
      </div>
      <section className="auth-stage" aria-labelledby="auth-title">
        <div className="auth-card">
          <h1 id="auth-title">
            {signup ? "Create your account." : "Welcome back."}
          </h1>
          <p className="auth-description">
            {signup
              ? "A private workspace for you and your team."
              : "Sign in to your PII Guard workspace."}
          </p>
          {loading ? (
            <LoadingIndicator label="Getting ready…" />
          ) : (
            <form
              className="auth-form"
              onSubmit={submit}
              noValidate
              aria-busy={submitting}
            >
              {signup && (
                <div className="auth-field">
                  <label htmlFor="auth-name">Your name</label>
                  <input
                    id="auth-name"
                    type="text"
                    autoComplete="name"
                    placeholder="Your name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                  />
                </div>
              )}
              <div className="auth-field">
                <label htmlFor="auth-email">Email</label>
                <input
                  id="auth-email"
                  type="text"
                  inputMode="email"
                  autoComplete="username"
                  placeholder="name@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoCapitalize="none"
                  spellCheck={false}
                />
              </div>
              <div className="auth-field">
                <label htmlFor="auth-password">Password</label>
                <div className="auth-password">
                  <input
                    id="auth-password"
                    type={showPassword ? "text" : "password"}
                    autoComplete={signup ? "new-password" : "current-password"}
                    placeholder="Enter your password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                  <button
                    className="auth-reveal"
                    type="button"
                    aria-label={
                      showPassword ? "Hide password" : "Show password"
                    }
                    aria-pressed={showPassword}
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? "Hide" : "Show"}
                  </button>
                </div>
              </div>
              {(loginError || error) && (
                <p className="auth-error" role="alert">
                  {loginError || error}
                </p>
              )}
              <button
                className="auth-submit"
                type="submit"
                disabled={submitting}
              >
                {submitting
                  ? signup
                    ? "Creating account…"
                    : "Signing in…"
                  : signup
                    ? "Create account"
                    : "Sign in"}
              </button>
              {submitting && (
                <LoadingIndicator
                  label={signup ? "Creating your workspace…" : "Signing in…"}
                />
              )}
            </form>
          )}
          <p className="auth-switch">
            {signup ? "Already have an account?" : "New to PII Guard?"}{" "}
            <Link
              to={signup ? "/login" : "/signup"}
              onClick={() => setLoginError("")}
            >
              {signup ? "Sign in" : "Create an account"}
            </Link>
          </p>
        </div>
        <p className="auth-note">Privacy starts with your workspace.</p>
      </section>
      <div className="auth-bottom">PII Guard · Built for your team</div>
    </div>
  );
}
