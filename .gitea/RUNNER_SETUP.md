# Gitea Actions Setup Guide

## Components

1. **Actions Runner** (`services/claude-ops-sandbox/gitea-runner/`)
   - Container: `gitea/act_runner:latest`
   - Registers with Gitea instance
   - Listens for webhook events (PR creation, updates)
   - Executes workflows defined in `.gitea/workflows/`

2. **CI Workflow** (`.gitea/workflows/ci.yml`)
   - Runs on every PR to `main` or `dev`
   - Stages: Lint → Build → Unit Tests
   - Each stage independent; parallel execution where possible
   - Fails fast on first error

3. **Branch Protection** (`.gitea/branch-protection.sh`)
   - Requires 1 approval before merge
   - Blocks force pushes
   - Blocks direct commits (PRs only)
   - Can be enhanced to require CI pass (TODO: Gitea API support)

## Deployment Steps

### Step 1: Get the Runner Registration Token

1. Log in to Gitea admin account
2. Go to `Admin` → `Actions` → `Runners`
3. Click "Create new Runner Token"
4. Copy the token

### Step 2: Deploy Runner Container

From `/root/sandbox/homelab`:

```bash
export GITEA_RUNNER_TOKEN="<token-from-step-1>"
cd services/claude-ops-sandbox/gitea-runner
docker-compose up -d
```

### Step 3: Verify Runner

```bash
# Check logs
docker logs gitea-runner

# Should see:
# INFO Runner registered successfully

# Verify in Gitea UI:
# http://gitea.yourdomain.com:3010 → Admin → Actions → Runners
# Status should be: Online
```

### Step 4: Configure Branch Protection

```bash
cd /root/sandbox/homelab

# Set your Gitea admin token
export GITEA_ADMIN_TOKEN="<your-admin-token>"

# Run the protection script
./.gitea/branch-protection.sh
```

Or manually in Gitea UI:
1. Repo Settings → Branches
2. Add branch protection rule for `main`:
   - Require pull request reviews: ✓
   - Minimum reviews: 1
   - Dismiss stale reviews: ✓
   - Block on status checks: (requires act_runner v0.5.4+ API support)

## How PRs Flow

```
User creates PR on main/dev
        ↓
Gitea webhook fires
        ↓
Runner picks up job
        ↓
.gitea/workflows/ci.yml runs
  - Lint (conventional commits)
  - Build (language-aware)
  - Unit Tests (coverage check)
        ↓
Results posted back to PR
        ↓
PR blocks merge until approvals + (optional) CI pass
```

## Next: Security Scanning

Phase 2 additions:
- **SAST:** Semgrep, Trivy for container images
- **Secrets detection:** TruffleHog
- **Supply chain:** Snyk for dependencies

Ask @security_audit for priority and tool selection.

## Troubleshooting

### Runner won't register
- Check network: Can runner reach `http://gitea:3000`?
- Check token: Is it valid and not expired?
- Check logs: `docker logs gitea-runner | grep -i error`

### Workflow doesn't trigger
- Confirm runner online in Gitea UI
- Check webhook delivery: Repo Settings → Webhooks
- Look for "Gitea Actions" webhook and check recent deliveries

### Build/test failures
- Review job output in PR → "Checks" section
- Check if language/build tool detected correctly
- Ensure build commands match project structure

### Coverage threshold failures
- Coverage must be ≥80% or PR blocks
- Add `coverage` badge to README if available
- Run locally: `npm test -- --coverage` (or equivalent)

---

**Status:** Ready for sandbox validation. Once Matt approves workflow, promote runner + config to production (VM 101).
