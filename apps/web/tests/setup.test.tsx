import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { OrganizationForm } from "../src/features/setup/OrganizationForm";
import { EmployeeAssignments } from "../src/features/setup/EmployeeAssignments";
const manager = "00000000-0000-4000-8000-000000000001",
  employee = "00000000-0000-4000-8000-000000000002";
describe("company setup", () => {
  it("rejects blank names and trims valid input", async () => {
    const user = userEvent.setup(),
      save = vi.fn().mockResolvedValue(undefined);
    render(<OrganizationForm name="Demo" save={save} />);
    const input = screen.getByLabelText("Company name");
    await user.clear(input);
    await user.type(input, "   ");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(save).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toBeVisible();
    await user.clear(input);
    await user.type(input, " New company ");
    await user.click(screen.getByRole("button", { name: "Save" }));
    await waitFor(() => expect(save).toHaveBeenCalledWith("New company"));
  });
  it("shows only managers in assignment choices and reports failed saves", async () => {
    const user = userEvent.setup(),
      save = vi.fn().mockRejectedValue(new Error("Rejected"));
    render(
      <EmployeeAssignments
        users={[
          {
            id: manager,
            email: "manager@example.com",
            display_name: "Manager",
            role: "manager",
          },
          {
            id: employee,
            email: "employee@example.com",
            display_name: "Employee",
            role: "employee",
          },
        ]}
        assignments={[]}
        save={save}
      />,
    );
    expect(screen.getAllByRole("option")).toHaveLength(2);
    await user.selectOptions(screen.getByRole("combobox"), manager);
    await waitFor(() =>
      expect(screen.getByRole("alert")).toHaveTextContent("Rejected"),
    );
    expect(save).toHaveBeenCalledWith(employee, manager);
  });
});
