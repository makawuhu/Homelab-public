# Hermes Operations Policy

Defines what any constrained agent (Hermes, Khris, Max, or any future assistant) may do in this repo without additional human approval, and what requires explicit instruction or a merged PR.

> **Status:** Active. Fully operational as of PR9 (2026-05-01). PRs 1–9 are complete.
> All infrastructure referenced here exists. No `[future]` items remain.

For a quick lookup of change types and their required gate, see [`CHANGE_CLASSES.md`](CHANGE_CLASSES.md).

---

## Trust model

Agents operate under a **read-propose-approve** model:

- **Read** anything in this repo at any time.
- **Propose** changes via PR. CI validates automatically.
- **Execute** only what a human has explicitly approved (merged a PR, or given direct instruction).

No agent has unilateral authority to deploy to production, modify live infrastructure, or take destructive actions. Claude (CT 102) is the GitOps controller; assistant agents (Khris, Max, Anri, Tao) may propose but not execute.

---

## Role assignments

| Agent | Node | Role | GitOps authority |
|-------|------|------|-----------------|
| Claude | CT 102 | GitOps controller, primary ops | Owns production. May merge PRs on human instruction. |
| Khris | CT 103 | Hermes assistant, Discord | Propose only. No production ops. |
| Max | CT 135 | OpenCode assistant, CLI | Propose only. No production ops. |
| Anri | CT 129 | Personal agent | Propose only. No infra access. |
| Tao | CT 133 | Info operator | Read-only. No repo access. |

---

## Permitted without approval

Any agent may do these without a PR or explicit instruction:

- Read any file in this repo, `CLAUDE.md`, `README.md`, service READMEs, `docs/ops/` policy docs
- Run `python3 scripts/validate_inventory.py` locally to check inventory consistency
- Run `python3 scripts/gen_docs.py --check` locally to check for doc drift
- Run `bash -n <script>` syntax checks on any shell script
- Open a PR with proposed changes — CI runs automatically

---

## Permitted with human approval (PR merge)

These changes go through the standard PR → CI → human review → merge flow. See [`CHANGE_CLASSES.md`](CHANGE_CLASSES.md) for per-class detail.

- Any documentation change (`README.md`, service READMEs, `docs/`)
- `inventory/hosts.yaml` or `inventory/services.yaml` additions or updates
- `service.yaml` field updates for any service
- `compose.yml` or `.deploy` changes for services with `risk_level: low` in `service.yaml`
- New service scaffolding via `scripts/new-service.sh`
- Script changes under `scripts/` (non-webhook)
- Renovate-generated image bumps (automated PRs, still require CI green + merge)

Merging a PR to `main` triggers the GitOps webhook, which auto-deploys any changed services that have a `.deploy` file and `deployable: true` in `service.yaml`.

---

## Requires explicit human instruction (never default path)

These actions require the human to explicitly ask, not just approve a PR:

- Deploy any service with `risk_level: medium` — confirm intent before running
- Deploy any service with `risk_level: high` — confirm intent + review data impact
- Deploy any service with `risk_level: manual-only` — human executes directly; agent does not run the deploy script
- Modify `services/webhook/` — this is the deploy pipeline itself; changes here affect all GitOps
- Modify `services/renovate/` — changes affect the automated dependency update pipeline
- Decrypt, rotate, or re-encrypt any `.env.sops` or `secrets/*.sops` file
- Any action involving `data_paths` listed in `service.yaml` — volumes, backups, restores
- Any Proxmox-level operation: start/stop VM/LXC, snapshot, destroy, resize, migrate
- Any change to OPNsense firewall rules or network topology
- Running `scripts/patching/orchestrate.sh` out of schedule

---

## Never (hard limits)

These are never permitted regardless of instructions:

- Force-push to `main` or any protected branch
- Delete branches or tags without explicit confirmation
- Run `docker volume rm`, `docker system prune`, or equivalent destructive storage ops
- Approve your own PRs
- Modify this policy file or `CHANGE_CLASSES.md` without human instruction
- Take any action on `services/immich/` beyond reading — photo library is irreplaceable
- SSH to any host and run arbitrary commands that bypass the GitOps deploy path, unless the human explicitly says "run this command"

---

## Safe wrappers

When running deploy scripts, use the shared library at `scripts/lib/deploy-helpers.sh`. It provides:

- `preflight_ssh <host>` — verify SSH reachability before starting
- `require_secrets <file…>` — check secret files exist before starting
- `remote_compose_deploy <host> <dir> <compose>` — standard SSH deploy pattern
- `npm_proxy_upsert` / `unbound_dns_upsert` — idempotent NPM + DNS operations
- `wait_for_http <url> <tries> <interval> <label>` — post-deploy health check

All service `deploy.sh` scripts that do remote ops source this library. Prefer these wrappers over raw SSH one-liners.

---

## CI gates

Every PR must pass CI before merge. CI runs:

```
python3 scripts/validate_inventory.py   # 13 checks across inventory + service.yaml + .deploy
```

A PR that fails CI must not be merged, even if the change looks trivial.

---

## Why these constraints exist

A prior agent setup (CT 103, April 2026) led to a near-data-loss incident. The root cause was not model capability — it was repo complexity combined with insufficient guardrails. This policy, combined with explicit `service.yaml` risk classifications, CI validation, and shared safe wrappers, is what makes constrained agent operation safe.

The goal is not a smarter agent. The goal is a simpler, more explicit repo where the right thing to do is also the easy thing to do.
