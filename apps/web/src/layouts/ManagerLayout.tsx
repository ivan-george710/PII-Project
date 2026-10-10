import { Outlet, useLocation } from "react-router-dom";
import { WorkspaceShell } from "../components/WorkspaceShell";

export function ManagerLayout() {
  const location = useLocation();
  return <WorkspaceShell title={location.pathname.includes("reports") ? "Employee reports" : "Company rules"}>
    <div className="settings-content"><Outlet /></div>
  </WorkspaceShell>;
}
