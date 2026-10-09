export function ReportFilters({
  filters,
  disabled,
}: {
  filters: {
    employeeId: string;
    setEmployeeId: (val: string) => void;
    category: string;
    setCategory: (val: string) => void;
    action: string;
    setAction: (val: string) => void;
    fromTime: string;
    setFromTime: (val: string) => void;
    toTime: string;
    setToTime: (val: string) => void;
  };
  disabled: boolean;
}) {
  return (
    <fieldset disabled={disabled} style={{ marginBottom: "1.5rem", padding: "1rem" }}>
      <legend>Report Filters</legend>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <label htmlFor="filter-employee">Employee ID</label>
          <input
            id="filter-employee"
            type="text"
            value={filters.employeeId}
            onChange={(e) => filters.setEmployeeId(e.target.value.trim())}
            placeholder="UUID (optional)"
          />
        </div>

        <div>
          <label htmlFor="filter-category">Category / Rule</label>
          <input
            id="filter-category"
            type="text"
            value={filters.category}
            onChange={(e) => filters.setCategory(e.target.value.trim())}
            placeholder="e.g. Financial"
          />
        </div>

        <div>
          <label htmlFor="filter-action">Action</label>
          <select
            id="filter-action"
            value={filters.action}
            onChange={(e) => filters.setAction(e.target.value)}
          >
            <option value="">All Actions</option>
            <option value="redacted">Redacted</option>
            <option value="allowed_disabled">Allowed (Disabled Rule)</option>
          </select>
        </div>

        <div>
          <label htmlFor="filter-from-time">From</label>
          <input
            id="filter-from-time"
            type="datetime-local"
            value={filters.fromTime}
            onChange={(e) => filters.setFromTime(e.target.value)}
          />
        </div>

        <div>
          <label htmlFor="filter-to-time">To</label>
          <input
            id="filter-to-time"
            type="datetime-local"
            value={filters.toTime}
            onChange={(e) => filters.setToTime(e.target.value)}
          />
        </div>
      </div>
    </fieldset>
  );
}
