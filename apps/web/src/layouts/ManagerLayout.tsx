import { NavLink, Outlet } from "react-router-dom";

export function ManagerLayout() {
  return (
    <div>
      <nav
        aria-label="Manager sections"
        style={{
          borderBottom: "1px solid #000",
          marginBottom: "1.5rem",
          display: "flex",
          gap: "1rem",
          paddingBottom: "0.5rem",
        }}
      >
        <NavLink
          to="/manager/settings"
          style={({ isActive }) => ({
            fontWeight: isActive ? "bold" : "normal",
            textDecoration: isActive ? "underline" : "none",
            color: "#000",
          })}
        >
          Rules & Policy
        </NavLink>
        <NavLink
          to="/manager/reports"
          style={({ isActive }) => ({
            fontWeight: isActive ? "bold" : "normal",
            textDecoration: isActive ? "underline" : "none",
            color: "#000",
          })}
        >
          Employee Reports
        </NavLink>
        <NavLink
          to="/company/setup"
          style={({ isActive }) => ({
            fontWeight: isActive ? "bold" : "normal",
            textDecoration: isActive ? "underline" : "none",
            color: "#000",
          })}
        >
          Company Setup
        </NavLink>
      </nav>
      <Outlet />
    </div>
  );
}
