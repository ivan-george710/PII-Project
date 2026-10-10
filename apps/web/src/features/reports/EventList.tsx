import { type ReportEvent } from "../../lib/schemas";

export function EventList({
  events,
  onSelectEvent,
  onLoadMore,
  hasMore,
  loading,
}: {
  events: ReportEvent[];
  onSelectEvent: (event: ReportEvent) => void;
  onLoadMore: () => void;
  hasMore: boolean;
  loading: boolean;
}) {
  if (events.length === 0) {
    return <p>No audit events match the current filters.</p>;
  }

  return (
    <section>
      <h2>Submissions ({events.length})</h2>
      <ul style={{ listStyle: "none", padding: 0 }}>
        {events.map((evt) => (
          <li
            key={evt.id}
            style={{
              border: "1px solid #ccc",
              padding: "0.75rem",
              marginBottom: "0.5rem",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div>
              <div>
                <strong>{evt.employee.display_name}</strong> ·{" "}
                {new Date(evt.occurred_at).toLocaleDateString()}
              </div>
              <small>
                Policy v{evt.policy_version} · Status: {evt.status} · Findings:{" "}
                {evt.total_findings}
              </small>
            </div>
            <button type="button" onClick={() => onSelectEvent(evt)}>
              View details
            </button>
          </li>
        ))}
      </ul>

      {hasMore && (
        <button
          type="button"
          disabled={loading}
          onClick={onLoadMore}
          style={{ marginTop: "1rem" }}
        >
          {loading ? "Loading more…" : "Load more"}
        </button>
      )}
    </section>
  );
}
