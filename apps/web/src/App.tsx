import { LoadingIndicator } from "./components/LoadingIndicator";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./features/auth/AuthProvider";
import { RequireAuth } from "./features/auth/RequireAuth";
import { useAuth } from "./features/auth/useAuth";
import Login from "./pages/Login";
import CompanySetup from "./pages/CompanySetup";
import ManagerSettings from "./pages/ManagerSettings";
import ManagerReports from "./pages/ManagerReports";
import { ManagerLayout } from "./layouts/ManagerLayout";
import Chat from "./pages/Chat";

function Home() {
  const { identity, loading } = useAuth();
  if (loading) return <LoadingIndicator label="Getting ready…" />;
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
  const { identity } = useAuth();
  return (
    <main className={identity ? undefined : "auth-main"}>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Login />} />
        <Route
          path="/company/setup"
          element={
            <RequireAuth manager>
              <CompanySetup />
            </RequireAuth>
          }
        />
        <Route
          path="/manager"
          element={
            <RequireAuth manager>
              <ManagerLayout />
            </RequireAuth>
          }
        >
          <Route path="settings" element={<ManagerSettings />} />
          <Route path="reports" element={<ManagerReports />} />
        </Route>
        <Route
          path="/chat"
          element={
            <RequireAuth>
              <Chat />
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
