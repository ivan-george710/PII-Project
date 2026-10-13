# Workflows

`test.yml` tests backend, frontend, builds and manager isolation on main/pseudofix. `deploy-manager.yml` deploys only frontend and manager source to the existing pii-guard Vercel project after successful main CI, or on manual dispatch. It uses the existing repository Vercel secret and IDs, and checks the public manager API/database after deployment. Employee engines, samples, private inputs and credentials are excluded from the deployment package.
