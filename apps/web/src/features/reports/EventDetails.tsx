import { type ReportEvent } from "../../lib/schemas";

export function EventDetails({
  event,
  onClose,
}: {
  event: ReportEvent;
  onClose: () => void;
}) {
  return (
    <div
      role="dialog"
      aria-labelledby="event-details-title"
      style={{
        border: "2px solid #000",
        padding: "1rem",
        marginBottom: "1.5rem",
        backgroundColor: "#fafafa",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <h3 id="event-details-title">Submission Audit Details</h3>
        <button type="button" onClick={onClose}>
          Close
        </button>
      </div>

      <p>
        <strong>Employee:</strong> {event.employee.display_name} ({event.employee.email})
      </p>
      <p>
        <strong>Occurred:</strong> {new Date(event.occurred_at).toLocaleString()}
      </p>
      <p>
        <strong>Policy Version:</strong> {event.policy_version} |{" "}
        <strong>Status:</strong> {event.status}
        {event.failure_code && ` (${event.failure_code})`}
      </p>

      <h4>Findings ({event.total_findings} total)</h4>
      {event.findings.length === 0 ? (
        <p>No PII detected in this submission.</p>
      ) : (
        <ul style={{ listStyle: "none", padding: 0 }}>
          {event.findings.map((f, idx) => (
            <li
              key={idx}
              style={{
                border: "1px solid #ccc",
                padding: "0.75rem",
                marginBottom: "0.5rem",
                backgroundColor: "#fff",
              }}
            >
              <div>
                <strong>{f.rule_id}</strong> — {f.category} (
                <span>Action: {f.action}</span>)
              </div>
              <div>Count: {f.count}</div>
              {f.locations.length > 0 && (
                <div style={{ marginTop: "0.25rem" }}>
                  <small>
                    Locations:{" "}
                    {f.locations
                      .map((loc, lIdx) => {
                        const parts: string[] = [loc.kind];
                        if (loc.page_number) parts.push(`p.${loc.page_number}`);
                        if (loc.slide_number) parts.push(`s.${loc.slide_number}`);
                        if (loc.start !== undefined && loc.end !== undefined) {
                          parts.push(`offset ${loc.start}–${loc.end}`);
                        }
                        return parts.join(" ");
                      })
                      .join("; ")}
                  </small>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
