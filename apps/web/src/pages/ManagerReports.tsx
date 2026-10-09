import { useState } from "react";
import { EventDetails } from "../features/reports/EventDetails";
import { EventList } from "../features/reports/EventList";
import { ReportFilters } from "../features/reports/ReportFilters";
import { useReports } from "../features/reports/useReports";
import { type ReportEvent } from "../lib/schemas";

export default function ManagerReports() {
  const {
    events,
    summary,
    nextCursor,
    loading,
    error,
    reload,
    loadMore,
    filters,
  } = useReports();

  const [selectedEvent, setSelectedEvent] = useState<ReportEvent | null>(null);

  if (loading && !summary && events.length === 0) {
    return <p role="status">Loading reports…</p>;
  }

  return (
    <section>
      <header>
        <h1>Employee PII Reports</h1>
        <p>Audit trail of assigned employees’ prompt submissions and redaction actions.</p>
      </header>

      {error && (
        <div role="alert" style={{ marginBottom: "1rem" }}>
          <p>{error}</p>
          <button onClick={() => void reload()}>Retry</button>
        </div>
      )}

      {summary && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
            gap: "1rem",
            marginBottom: "1.5rem",
          }}
        >
          <div style={{ border: "1px solid #ccc", padding: "1rem" }}>
            <small>Submissions</small>
            <div style={{ fontSize: "1.5rem", fontWeight: "bold" }}>
              {summary.submission_count}
            </div>
          </div>
          <div style={{ border: "1px solid #ccc", padding: "1rem" }}>
            <small>Redacted</small>
            <div style={{ fontSize: "1.5rem", fontWeight: "bold" }}>
              {summary.redacted_count}
            </div>
          </div>
          <div style={{ border: "1px solid #ccc", padding: "1rem" }}>
            <small>Allowed (Disabled)</small>
            <div style={{ fontSize: "1.5rem", fontWeight: "bold" }}>
              {summary.allowed_disabled_count}
            </div>
          </div>
          <div style={{ border: "1px solid #ccc", padding: "1rem" }}>
            <small>Failed</small>
            <div style={{ fontSize: "1.5rem", fontWeight: "bold" }}>
              {summary.failed_count}
            </div>
          </div>
        </div>
      )}

      <ReportFilters filters={filters} disabled={loading} />

      {selectedEvent && (
        <EventDetails
          event={selectedEvent}
          onClose={() => setSelectedEvent(null)}
        />
      )}

      <EventList
        events={events}
        onSelectEvent={setSelectedEvent}
        onLoadMore={loadMore}
        hasMore={Boolean(nextCursor)}
        loading={loading}
      />
    </section>
  );
}
