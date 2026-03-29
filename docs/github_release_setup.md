# GitHub Release Setup

This repo now includes:

- CI workflow for lint, tests, and Docker build on push/PR to `main` and `master`
- GHCR publish workflow on version tags (`v*`) and manual dispatch

## Recommended Repository Settings

### Branch protection

Protect `main` with:

- Require pull request before merging
- Require status checks to pass before merging
- Require branches to be up to date before merging

Recommended required checks:

- `lint-and-test`
- `docker-build`

### GHCR publish

The workflow publishes images to:

- `ghcr.io/<owner>/arxiv-paper-mcp`

Release flow:

```bash
git tag v1.0.0
git push origin v1.0.0
```

The workflow uses `GITHUB_TOKEN` with `packages: write`, so no extra registry
secret is required for publishing to the same repository owner namespace.

### Optional Sonar setup

Sonar was intentionally left out of the default workflow until repo-level values
are available.

If you want Sonar on PRs/pushes later, add:

- repository secret: `SONAR_TOKEN`
- repository variable: `SONAR_PROJECT_KEY`
- repository variable: `SONAR_ORGANIZATION`

Then add a Sonar job back into CI or a dedicated workflow.
