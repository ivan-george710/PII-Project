import { useOrganization } from "../features/setup/useOrganization";
import { OrganizationForm } from "../features/setup/OrganizationForm";
import { EmployeeAssignments } from "../features/setup/EmployeeAssignments";
import { AddEmployeeForm } from "../features/setup/AddEmployeeForm";
import { useAuth } from "../features/auth/useAuth";
import { WorkspaceShell } from "../components/WorkspaceShell";
import { LoadingIndicator } from "../components/LoadingIndicator";
export default function CompanySetup() {
  const state = useOrganization();
  const { identity } = useAuth();
  return (
    <WorkspaceShell title="Workspace settings">
      <div className="settings-content">
        <div className="settings-heading">
          <h1>Company setup</h1>
          <p>
            One workspace for your team. Add employees and choose who they
            report to.
          </p>
        </div>
        {state.loading ? (
          <LoadingIndicator label="Loading workspace…" />
        ) : state.error || !state.company ? (
          <div className="form-error">
            <p role="alert">{state.error || "Company unavailable"}</p>
            <button onClick={() => void state.reload()}>Try again</button>
          </div>
        ) : (
          <>
            <section className="settings-section">
              <div className="section-heading">
                <h2>Workspace</h2>
                <p>The name your team sees when they sign in.</p>
              </div>
              <OrganizationForm name={state.company.name} save={state.rename} />
            </section>
            <AddEmployeeForm
              managers={state.users.filter((u) => u.role === "manager")}
              currentManager={identity!.user.id}
              save={state.addEmployee}
            />
            <EmployeeAssignments
              users={state.users}
              assignments={state.assignments}
              save={state.assign}
            />
          </>
        )}
      </div>
    </WorkspaceShell>
  );
}
