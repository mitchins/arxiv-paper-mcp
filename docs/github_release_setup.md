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

Supported published platforms:

- `linux/amd64`
- `linux/arm64`

Release flow:

```bash
git tag v1.0.0
git push origin v1.0.0
```

Dry-run flow (manual dispatch from Actions UI):

- Run `Publish Docker Image` on your branch before tagging.
- Validate pull/run on your host architecture with the `sha-<commit>` tag.

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
