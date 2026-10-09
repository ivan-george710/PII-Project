import { useCallback, useEffect, useState } from "react";
import { api } from "../../lib/api";
import {
  reportEventsPage,
  reportSummary,
  type ReportEvent,
  type ReportSummary,
} from "../../lib/schemas";
import { useAuth } from "../auth/useAuth";

export function useReports() {
  const { identity } = useAuth();
  const [events, setEvents] = useState<ReportEvent[]>([]);
  const [summary, setSummary] = useState<ReportSummary | null>(null);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters state
  const [employeeId, setEmployeeId] = useState<string>("");
  const [category, setCategory] = useState<string>("");
  const [action, setAction] = useState<string>("");
  const [fromTime, setFromTime] = useState<string>("");
  const [toTime, setToTime] = useState<string>("");

  const csrf = identity?.csrf_token;

  const buildQuery = useCallback(
    (cursor?: string) => {
      const params = new URLSearchParams();
      if (employeeId) params.append("employee_id", employeeId);
      if (category) params.append("category", category);
      if (action) params.append("action", action);
      if (fromTime) params.append("from_time", fromTime);
      if (toTime) params.append("to_time", toTime);
      if (cursor) params.append("cursor", cursor);
      params.append("limit", "25");
      const qs = params.toString();
      return qs ? `?${qs}` : "";
    },
    [employeeId, category, action, fromTime, toTime]
  );

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const summaryQuery = (() => {
        const p = new URLSearchParams();
        if (employeeId) p.append("employee_id", employeeId);
        if (category) p.append("category", category);
        if (action) p.append("action", action);
        if (fromTime) p.append("from_time", fromTime);
        if (toTime) p.append("to_time", toTime);
        const qs = p.toString();
        return qs ? `?${qs}` : "";
      })();

      const [eventsRes, summaryRes] = await Promise.all([
        api(`/reports${buildQuery()}`, reportEventsPage, {}, csrf),
        api(`/reports/summary${summaryQuery}`, reportSummary, {}, csrf),
      ]);

      setEvents(eventsRes.items);
      setNextCursor(eventsRes.next_cursor);
      setSummary(summaryRes);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load reports");
    } finally {
      setLoading(false);
    }
  }, [buildQuery, csrf, employeeId, category, action, fromTime, toTime]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const loadMore = async () => {
    if (!nextCursor || loading) return;
    try {
      const res = await api(`/reports${buildQuery(nextCursor)}`, reportEventsPage, {}, csrf);
      setEvents((prev) => [...prev, ...res.items]);
      setNextCursor(res.next_cursor);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load next page");
    }
  };

  return {
    events,
    summary,
    nextCursor,
    loading,
    error,
    reload: loadData,
    loadMore,
    filters: {
      employeeId,
      setEmployeeId,
      category,
      setCategory,
      action,
      setAction,
      fromTime,
      setFromTime,
      toTime,
      setToTime,
    },
  };
}
