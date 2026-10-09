import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./features/auth/AuthProvider";
import { RequireAuth } from "./features/auth/RequireAuth";
import { useAuth } from "./features/auth/useAuth";
import Login from "./pages/Login";
import CompanySetup from "./pages/CompanySetup";
import Chat from "./pages/Chat";
function Home() {
  const { identity, loading } = useAuth();
  if (loading) return <p role="status">Loading…</p>;
  return (
    <Navigate
      to={
        !identity
          ? "/login"
          : identity.user.role === "manager"
            ? "/company/setup"
            : "/chat"
      }
      replace
    />
  );
}
function Shell() {
  const { identity, logout } = useAuth();
  return (
    <main>
      {identity && (
        <header>
          <span>
            {identity.organization.name} · {identity.user.display_name}
          </span>
          <button onClick={() => void logout()}>Sign out</button>
        </header>
      )}
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/company/setup"
          element={
            <RequireAuth manager>
              <CompanySetup />
            </RequireAuth>
          }
        />
        <Route
          path="/chat"
          element={
            <RequireAuth>
              <section>
                <Chat />
              </section>
            </RequireAuth>
          }
        />
        <Route path="*" element={<Home />} />
      </Routes>
    </main>
  );
}
export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Shell />
      </AuthProvider>
    </BrowserRouter>
  );
}
