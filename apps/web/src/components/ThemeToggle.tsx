import { useEffect, useState } from "react";
export function ThemeToggle() {
  const [theme, setTheme] = useState(() => {
    try {
      const saved = localStorage.getItem("pii-theme");
      return saved === "light" || saved === "dark" ? saved : "system";
    } catch {
      return "system";
    }
  });
  useEffect(() => {
    const media = window.matchMedia?.("(prefers-color-scheme: dark)");
    const apply = () => {
      document.documentElement.dataset.theme =
        theme === "system" ? (media?.matches ? "dark" : "light") : theme;
    };
    apply();
    try {
      localStorage.setItem("pii-theme", theme);
    } catch {
      /* Storage can be disabled. */
    }
    media?.addEventListener("change", apply);
    return () => media?.removeEventListener("change", apply);
  }, [theme]);
  return (
    <label className="theme-control">
      <span>Appearance</span>
      <select
        aria-label="Appearance"
        value={theme}
        onChange={(e) => setTheme(e.target.value)}
      >
        <option value="system">System</option>
        <option value="light">Light</option>
        <option value="dark">Dark</option>
      </select>
    </label>
  );
}
