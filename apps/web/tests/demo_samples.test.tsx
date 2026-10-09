import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { AttachmentMenu } from "../src/features/chat/AttachmentMenu";

const messageSample = {
  id: "11000000-0000-4000-8000-000000000001",
  kind: "message" as const,
  title: "Contact details",
  description: "Fictional details",
  tags: ["text_pii" as const],
  text: "Fictional contact example",
};
const fileSample = {
  id: "22000000-0000-4000-8000-000000000001",
  kind: "file" as const,
  title: "Native PDF",
  description: "Synthetic PDF",
  tags: ["text_pii" as const],
  filename: "text.pdf",
  mime_type: "application/pdf" as const,
  size_bytes: 200,
};

describe("sample menu", () => {
  it("opens accessibly and selects message and file examples without sending", async () => {
    const user = userEvent.setup();
    const select = vi.fn();
    render(
      <AttachmentMenu
        onUpload={vi.fn()}
        samples={[messageSample, fileSample]}
        loading={false}
        error=""
        selecting={null}
        onSelectSample={select}
        onRetrySamples={vi.fn()}
        disabled={false}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Add attachment" }));
    const submenu = screen.getByRole("menuitem", { name: "Try test data" });
    await user.click(submenu);
    expect(submenu).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByRole("region", { name: "Message examples" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Contact details/ }));
    expect(select).toHaveBeenCalledWith(messageSample);
    await user.click(screen.getByRole("button", { name: /Native PDF/ }));
    expect(select).toHaveBeenCalledWith(fileSample);
  });

  it("shows catalog loading and errors", async () => {
    const user = userEvent.setup();
    render(
      <AttachmentMenu
        onUpload={vi.fn()}
        samples={[]}
        loading
        error="Samples unavailable"
        selecting={null}
        onSelectSample={vi.fn()}
        onRetrySamples={vi.fn()}
        disabled={false}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Add attachment" }));
    await user.click(screen.getByRole("menuitem", { name: "Try test data" }));
    expect(screen.getByRole("status")).toHaveTextContent("Loading samples");
    expect(screen.getByRole("alert")).toHaveTextContent("Samples unavailable");
    await user.click(screen.getByRole("button", { name: "Retry" }));
  });
});
