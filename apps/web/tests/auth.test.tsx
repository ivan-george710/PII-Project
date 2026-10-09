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
      vi.fn().mockResolvedValue(
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

import userEvent from "@testing-library/user-event";
import { Routes, Route } from "react-router-dom";
import Login from "../src/pages/Login";

describe("local sign-in", () => {
  function renderLogin(path = "/login") {
    return render(
      <MemoryRouter initialEntries={[path]}>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Login />} />
            <Route path="/company/setup" element={<p>Company setup</p>} />
          </Routes>
        </AuthProvider>
      </MemoryRouter>,
    );
  }
  it("submits credentials and navigates using the server role", async () => {
    const manager = { ...value, user: { ...value.user, role: "manager" } };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response("{}", { status: 401 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(manager)))
      .mockResolvedValueOnce(new Response(JSON.stringify(manager)));
    vi.stubGlobal("fetch", fetchMock);
    renderLogin();
    await screen.findByRole("button", { name: "Sign in" });
    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Email"), "MANAGER@example.com");
    await user.type(
      screen.getByLabelText("Password"),
      "fictional-password-123",
    );
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    await screen.findByText("Company setup");
    expect(fetchMock.mock.calls[1][0]).toBe("/api/v1/auth/login");
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({
      email: "manager@example.com",
      password: "fictional-password-123",
    });
    expect(fetchMock.mock.calls[1][1].credentials).toBe("same-origin");
  });
  it("shows failed login feedback without navigating", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(new Response("{}", { status: 401 }))
        .mockResolvedValueOnce(
          new Response(
            JSON.stringify({
              error: {
                code: "INVALID_CREDENTIALS",
                message: "Email or password is incorrect",
                fields: [],
                request_id: "00000000-0000-4000-8000-000000000001",
              },
            }),
            { status: 401 },
          ),
        ),
    );
    renderLogin();
    await screen.findByRole("button", { name: "Sign in" });
    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Email"), "manager@example.com");
    await user.type(screen.getByLabelText("Password"), "wrong-password-123");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Email or password is incorrect",
    );
    expect(screen.queryByText("Company setup")).not.toBeInTheDocument();
  });
  it("offers signup and submits unchecked credentials", async () => {
    const manager = {
      ...value,
      user: { ...value.user, role: "manager", email: "anything" },
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response("{}", { status: 401 }))
      .mockResolvedValueOnce(
        new Response(JSON.stringify(manager), { status: 201 }),
      )
      .mockResolvedValueOnce(new Response(JSON.stringify(manager)));
    vi.stubGlobal("fetch", fetchMock);
    renderLogin();
    const user = userEvent.setup();
    await user.click(
      await screen.findByRole("link", { name: "Create an account" }),
    );
    await screen.findByRole("heading", { name: "Create your account." });
    await user.type(screen.getByLabelText("Your name"), "Ada");
    await user.type(screen.getByLabelText("Email"), "anything");
    await user.type(screen.getByLabelText("Password"), "x");
    expect(screen.getByLabelText("Email")).not.toHaveAttribute("type", "email");
    expect(screen.getByLabelText("Password")).not.toHaveAttribute("minlength");
    await user.click(screen.getByRole("button", { name: "Show password" }));
    expect(screen.getByLabelText("Password")).toHaveAttribute("type", "text");
    await user.click(screen.getByRole("button", { name: "Create account" }));
    await screen.findByText("Company setup");
    expect(fetchMock.mock.calls[1][0]).toBe("/api/v1/auth/signup");
    expect(JSON.parse(fetchMock.mock.calls[1][1].body)).toEqual({
      email: "anything",
      password: "x",
      display_name: "Ada",
    });
  });
});
