import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AddEmployeeForm } from "../src/features/setup/AddEmployeeForm";
const manager = "00000000-0000-4000-8000-000000000001";
const managers = [
  {
    id: manager,
    email: "manager",
    display_name: "Manager",
    role: "manager" as const,
  },
];
describe("employee creation", () => {
  it("accepts unrestricted credentials and creates an assigned workspace employee", async () => {
    const user = userEvent.setup();
    const save = vi
      .fn()
      .mockResolvedValue({ user: { display_name: "Jordan" } });
    render(
      <AddEmployeeForm
        managers={managers}
        currentManager={manager}
        save={save}
      />,
    );
    await user.type(screen.getByLabelText("Full name"), " Jordan ");
    await user.type(screen.getByLabelText("Employee email"), "NOT-AN-EMAIL");
    await user.click(screen.getByRole("button", { name: "Add employee" }));
    await waitFor(() =>
      expect(save).toHaveBeenCalledWith({
        display_name: "Jordan",
        email: "not-an-email",
        password: "",
        manager_id: manager,
      }),
    );
    expect(screen.getByRole("status")).toHaveTextContent(
      "Jordan can now sign in",
    );
    expect(screen.getByLabelText("Employee email")).toHaveValue("");
  });
  it("keeps inputs and reports rejected creation without claiming success", async () => {
    const user = userEvent.setup();
    const save = vi
      .fn()
      .mockRejectedValue(
        new Error("An account with this email already exists"),
      );
    render(
      <AddEmployeeForm
        managers={managers}
        currentManager={manager}
        save={save}
      />,
    );
    await user.type(screen.getByLabelText("Full name"), "Jordan");
    await user.type(screen.getByLabelText("Employee email"), "existing");
    await user.type(screen.getByLabelText("Password"), "x");
    await user.click(screen.getByRole("button", { name: "Add employee" }));
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("already exists"),
    );
    expect(screen.getByLabelText("Employee email")).toHaveValue("existing");
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });
});
