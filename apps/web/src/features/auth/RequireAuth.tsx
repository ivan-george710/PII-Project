import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "./useAuth";
export function RequireAuth({
  children,
  manager = false,
}: {
  children: ReactNode;
  manager?: boolean;
}) {
  const { identity, loading, error } = useAuth();
  if (loading) return <p role="status">Loading…</p>;
  if (!identity) return <Navigate to="/login" replace state={{ error }} />;
  if (manager && identity.user.role !== "manager")
    return <Navigate to="/chat" replace />;
  return children;
}
