import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AuthProvider } from "../src/features/auth/AuthProvider";
import { useAuth } from "../src/features/auth/useAuth";
import { RequireAuth } from "../src/features/auth/RequireAuth";
import { AuthContext } from "../src/features/auth/AuthProvider";
import { session } from "../src/lib/schemas";
const value = {
  user: {
    id: "00000000-0000-4000-8000-000000000001",
    email: "test@example.com",
    display_name: "Employee",
    role: "employee" as const,
    organization_id: "00000000-0000-4000-8000-000000000002",
  },
  organization: { id: "00000000-0000-4000-8000-000000000002", name: "Demo" },
  csrf_token: "token",
};
function Probe() {
  const a = useAuth();
  return (
    <p>
      {a.loading
        ? "Loading"
        : a.identity
          ? a.identity.user.role
          : a.error || "Signed out"}
    </p>
  );
}
afterEach(() => vi.unstubAllGlobals());
describe("authentication", () => {
  it("rejects malformed API session payloads", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(JSON.stringify({ user: { role: "manager" } }), {
            status: 200,
          }),
        ),
    );
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() =>
      expect(screen.queryByText("Loading")).not.toBeInTheDocument(),
    );
    expect(screen.queryByText("manager")).not.toBeInTheDocument();
  });
  it("accepts validated identity and forbids unexpected privilege fields", async () => {
    expect(session.safeParse({ ...value, admin: true }).success).toBe(false);
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(JSON.stringify(value), { status: 200 }),
        ),
    );
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await screen.findByText("employee");
  });
  it("does not render manager setup for employee role", () => {
    render(
      <MemoryRouter>
        <AuthContext.Provider
          value={{
            identity: value,
            loading: false,
            error: "",
            reload: async () => {},
            logout: async () => {},
          }}
        >
          <RequireAuth manager>
            <p>Private setup</p>
          </RequireAuth>
        </AuthContext.Provider>
      </MemoryRouter>,
    );
    expect(screen.queryByText("Private setup")).not.toBeInTheDocument();
  });
});
