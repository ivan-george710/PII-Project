import { useOrganization } from "../features/setup/useOrganization";
import { OrganizationForm } from "../features/setup/OrganizationForm";
import { EmployeeAssignments } from "../features/setup/EmployeeAssignments";
export default function CompanySetup() {
  const state = useOrganization();
  if (state.loading) return <p role="status">Loading company…</p>;
  if (state.error || !state.company)
    return (
      <div>
        <p role="alert">{state.error || "Company unavailable"}</p>
        <button onClick={() => void state.reload()}>Retry</button>
      </div>
    );
  return (
    <section>
      <h1>Company setup</h1>
      <OrganizationForm name={state.company.name} save={state.rename} />
      <EmployeeAssignments
        users={state.users}
        assignments={state.assignments}
        save={state.assign}
      />
    </section>
  );
}
