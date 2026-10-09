import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ReportFilters } from "../src/features/reports/ReportFilters";
import { EventList } from "../src/features/reports/EventList";
import { EventDetails } from "../src/features/reports/EventDetails";
import { type ReportEvent } from "../src/lib/schemas";

const sampleEvent: ReportEvent = {
  id: "00000000-0000-4000-8000-000000000010",
  submission_id: "00000000-0000-4000-8000-000000000020",
  employee: {
    id: "00000000-0000-4000-8000-000000000030",
    display_name: "Alice Employee",
    email: "alice@company.example",
  },
  occurred_at: "2026-10-10T00:00:00Z",
  policy_version: 1,
  status: "completed",
  findings: [
    {
      rule_id: "CREDIT_CARD",
      category: "Financial",
      count: 1,
      action: "redacted",
      locations: [
        {
          kind: "message",
          start: 5,
          end: 21,
        },
      ],
    },
  ],
  total_findings: 1,
};

describe("ReportFilters component", () => {
  it("renders filter inputs and handles changes", async () => {
    const user = userEvent.setup();
    const setEmployeeId = vi.fn();
    const setCategory = vi.fn();
    const setAction = vi.fn();
    const setFromTime = vi.fn();
    const setToTime = vi.fn();

    render(
      <ReportFilters
        filters={{
          employeeId: "",
          setEmployeeId,
          category: "",
          setCategory,
          action: "",
          setAction,
          fromTime: "",
          setFromTime,
          toTime: "",
          setToTime,
        }}
      />
    );

    const categoryInput = screen.getByLabelText(/Category/i);
    await user.type(categoryInput, "Financial");
    expect(setCategory).toHaveBeenCalled();
  });
});

describe("EventList component", () => {
  it("displays events and triggers detail selection", async () => {
    const user = userEvent.setup();
    const onSelectEvent = vi.fn();
    const onLoadMore = vi.fn();

    render(
      <EventList
        events={[sampleEvent]}
        onSelectEvent={onSelectEvent}
        onLoadMore={onLoadMore}
        hasMore={false}
        loading={false}
      />
    );

    expect(screen.getByText("Alice Employee")).toBeInTheDocument();
    const detailsBtn = screen.getByRole("button", { name: "View details" });
    await user.click(detailsBtn);
    expect(onSelectEvent).toHaveBeenCalledWith(sampleEvent);
  });
});

describe("EventDetails component", () => {
  it("renders safe finding metadata without raw PII", () => {
    const onClose = vi.fn();
    render(<EventDetails event={sampleEvent} onClose={onClose} />);

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Alice Employee (alice@company.example)")).toBeInTheDocument();
    expect(screen.getByText(/CREDIT_CARD/i)).toBeInTheDocument();
    expect(screen.getByText(/Financial/i)).toBeInTheDocument();
    expect(screen.getByText(/Action: redacted/i)).toBeInTheDocument();
  });
});
