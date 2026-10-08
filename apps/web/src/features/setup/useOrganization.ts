import { useCallback, useEffect, useState } from "react";
import { api } from "../../lib/api";
import {
  organization,
  organizationInput,
  assignmentInput,
  assignment,
  assignmentsPage,
  usersPage,
} from "../../lib/schemas";
import { z } from "zod";
import { useAuth } from "../auth/useAuth";
export function useOrganization() {
  const { identity } = useAuth();
  const [company, setCompany] = useState<z.infer<typeof organization> | null>(
    null,
  );
  const [users, setUsers] = useState<z.infer<typeof usersPage>["items"]>([]);
  const [assignments, setAssignments] = useState<
    z.infer<typeof assignmentsPage>["items"]
  >([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const reload = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [company, firstUsers, firstAssignments] = await Promise.all([
        api("/organization", organization),
        api("/organization/users?limit=100", usersPage),
        api("/organization/assignments?limit=100", assignmentsPage),
      ]);
      const allUsers: typeof users = [];
      const allAssignments: typeof assignments = [];
      allUsers.push(...firstUsers.items);
      allAssignments.push(...firstAssignments.items);
      let cursor: string | null = firstUsers.next_cursor;
      while (cursor) {
        const page: z.infer<typeof usersPage> = await api(
          "/organization/users?limit=100" +
            (cursor ? `&cursor=${encodeURIComponent(cursor)}` : ""),
          usersPage,
        );
        allUsers.push(...page.items);
        cursor = page.next_cursor;
      }
      cursor = firstAssignments.next_cursor;
      while (cursor) {
        const page: z.infer<typeof assignmentsPage> = await api(
          "/organization/assignments?limit=100" +
            (cursor ? `&cursor=${encodeURIComponent(cursor)}` : ""),
          assignmentsPage,
        );
        allAssignments.push(...page.items);
        cursor = page.next_cursor;
      }
      setCompany(company);
      setUsers(allUsers);
      setAssignments(allAssignments);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load company");
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    void reload();
  }, [reload]);
  async function rename(name: string) {
    const input = organizationInput.parse({ name });
    setCompany(
      await api(
        "/organization",
        organization,
        { method: "PATCH", body: JSON.stringify(input) },
        identity?.csrf_token,
      ),
    );
  }
  async function assign(employee: string, manager: string) {
    if (manager)
      await api(
        `/organization/assignments/${employee}`,
        assignment,
        {
          method: "PUT",
          body: JSON.stringify(assignmentInput.parse({ manager_id: manager })),
        },
        identity?.csrf_token,
      );
    else
      await api(
        `/organization/assignments/${employee}`,
        z.undefined(),
        { method: "DELETE" },
        identity?.csrf_token,
      );
    await reload();
  }
  return {
    company,
    users,
    assignments,
    error,
    loading,
    rename,
    assign,
    reload,
  };
}
