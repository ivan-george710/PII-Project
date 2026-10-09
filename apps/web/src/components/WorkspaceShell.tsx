import { useState, useEffect, useRef, type ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../features/auth/useAuth";
import { BrandMark } from "./BrandMark";
import { ThemeToggle } from "./ThemeToggle";
export function WorkspaceShell({
  children,
  title,
  navigation,
}: {
  children: ReactNode;
  title: string;
  navigation?: ReactNode;
}) {
  const { identity, logout, error } = useAuth();
  const [open, setOpen] = useState(false);
  const sidebar = useRef<HTMLElement>(null);
  const menuButton = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!open) return;
    sidebar.current?.querySelector<HTMLButtonElement>(".mobile-close")?.focus();
    return () => menuButton.current?.focus();
  }, [open]);
  function trapFocus(e: React.KeyboardEvent<HTMLElement>) {
    if (!open) return;
    if (e.key === "Escape") {
      setOpen(false);
      return;
    }
    if (e.key !== "Tab") return;
    const items = sidebar.current?.querySelectorAll<HTMLElement>(
      "button:not(:disabled),a,select",
    );
    if (!items?.length) return;
    const first = items[0],
      last = items[items.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }
  return (
    <div className="workspace-shell">
      {open && (
        <button
          className="sidebar-backdrop"
          aria-label="Close navigation"
          onClick={() => setOpen(false)}
        />
      )}
      <aside
        ref={sidebar}
        role={open ? "dialog" : undefined}
        aria-modal={open ? true : undefined}
        className={`workspace-sidebar ${open ? "is-open" : ""}`}
        aria-label="Workspace navigation"
        onKeyDown={trapFocus}
      >
        <div className="sidebar-brand">
          <span className="brand-lockup">
            <BrandMark />
            PII Guard
          </span>
          <button
            className="mobile-close quiet-button"
            onClick={() => setOpen(false)}
          >
            Close
          </button>
        </div>
        <div
          className="sidebar-content"
          onClick={(e) => {
            if ((e.target as HTMLElement).closest("button,a")) setOpen(false);
          }}
        >
          {identity?.user.role === "manager" ? (
            <nav>
              <NavLink className="sidebar-link" to="/company/setup">
                Workspace settings
              </NavLink>
            </nav>
          ) : (
            navigation
          )}
        </div>
        <div className="sidebar-footer">
          <ThemeToggle />
          <div className="account-summary">
            <strong>{identity?.user.display_name || "Your account"}</strong>
            <span>{identity?.organization.name}</span>
          </div>
          <button
            className="quiet-button sign-out"
            onClick={() => void logout()}
          >
            Sign out
          </button>
          {error && (
            <p role="alert" className="form-error">
              {error}
            </p>
          )}
        </div>
      </aside>
      <div className="workspace-body" inert={open}>
        <header className="workspace-topbar">
          <button
            ref={menuButton}
            className="mobile-nav quiet-button"
            aria-expanded={open}
            onClick={() => setOpen(!open)}
          >
            Menu
          </button>
          <span>{title}</span>
          <span className="workspace-name">{identity?.organization.name}</span>
        </header>
        {children}
      </div>
    </div>
  );
}
