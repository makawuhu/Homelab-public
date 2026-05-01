# Homelab GitOps Manual

A plain-English guide to how this repo works, what we built, and the rules that govern it.

---

## Table of Contents

1. [The Big Picture](#1-the-big-picture)
2. [How GitOps Deploy Works](#2-how-gitops-deploy-works)
3. [The Inventory System](#3-the-inventory-system)
4. [service.yaml — What Each Service Declares](#4-serviceyaml--what-each-service-declares)
5. [The .deploy File](#5-the-deploy-file)
6. [Secrets Management](#6-secrets-management)
7. [The Validator (CI)](#7-the-validator-ci)
8. [Deploy Scripts and Safe Wrappers](#8-deploy-scripts-and-safe-wrappers)
9. [The Agent Ecosystem](#9-the-agent-ecosystem)
10. [The Rules — What Agents Can and Can't Do](#10-the-rules--what-agents-can-and-cant-do)
11. [Rules for You — The Human Operator](#11-rules-for-you--the-human-operator)
12. [Common Tasks](#12-common-tasks)

---

## 1. The Big Picture

This is a **GitOps repo** — git is the single source of truth for your homelab infrastructure. Every service that runs in your homelab has a directory under `services/`. When you merge a pull request, the infrastructure automatically updates to match what's in git.

The key insight: **you never SSH to a host and edit files directly** (for managed services). You edit the repo, open a PR, merge it, and the webhook handles the rest.

```
You edit files → open PR → CI validates → you merge → webhook fires → services update
```

The repo lives on Gitea at `your-gitea-user/homelab`. The machine that runs the webhook is **CT 102 (claude-ops)** at `192.168.x.8` — this is the ops controller that has SSH access to everything else.

---

## 2. How GitOps Deploy Works

### The webhook

When you merge a PR to `main`, Gitea fires a webhook to CT 102 on port 9000. The webhook handler script at `services/webhook/scripts/webhook-handler.sh` runs automatically:

1. **Syncs the repo** — `git fetch && git reset --hard origin/main`
2. **Detects what changed** — compares old HEAD to new HEAD, finds which `services/` directories were modified
3. **For each changed service that has a `.deploy` file:**
   - Reads the `.deploy` file to find the target host IP
   - Decrypts secrets if `.env.sops` exists, SCPs the `.env` to the target
   - SSHs to the target, pulls the latest compose file, runs `docker compose up -d`
4. **Reports results** — logs to `/var/log/deploy.log` on CT 102

### Local vs. remote deploy

Services can be deployed in two ways:

- **Local** (target is CT 102 itself, `192.168.x.8`): the webhook runs `docker compose up -d` directly
- **Remote** (target is any other host): the webhook SSHs to the host and runs the commands there

Most services target VM 101 (`192.168.x.5`), the primary Docker host.

### What triggers a deploy

Only services whose files actually changed get deployed. If you open a PR that only changes `services/jellyfin/compose.yml`, only Jellyfin gets redeployed — nothing else is touched.

### First-time deploys

The webhook handles *re-deploys* of existing services. When you're adding a brand-new service for the first time (creating DNS, NPM proxy, volumes, etc.), you run `services/<name>/deploy.sh` manually from CT 102. That's a one-time setup step. After that, all updates go through the GitOps webhook.

---

## 3. The Inventory System

The inventory is the canonical list of hosts and services. It has two files.

### `inventory/hosts.yaml`

Lists the 7 **deploy-target hosts** — machines that receive deployments from the webhook. Each host has a unique key, an IP, and a type (vm or lxc).

```yaml
portainer-vm:
  ip: "192.168.x.5"
  type: vm
  proxmox_id: 101
  description: "Primary Docker host, VM 101"

claude-ops:
  ip: "192.168.x.8"
  type: lxc
  proxmox_id: 102
  description: "GitOps operator CT 102"
```

Not every machine in the homelab is in `hosts.yaml` — only machines that receive GitOps deploys. Agents like Khris (CT 103) or Anri (CT 129) are documented in `services/` but not here, because they're managed externally.

### `inventory/services.yaml`

Lists every directory under `services/` and classifies it into one of four categories:

| Category | Meaning |
|----------|---------|
| `compose_managed` | Has a `compose.yml` + `.deploy` — fully managed by GitOps webhook |
| `special` | Has a `.deploy` but no `compose.yml` (e.g., the GPU VM — the VM itself is the unit) |
| `ct_resident` | Dedicated LXC/VM managed externally; documented here but not deployed via webhook |
| `doc_only` | Documentation stub only — no deployable artifact |

Example:
```yaml
homepage:
  category: compose_managed
  host: portainer-vm   # must match a key in hosts.yaml

khris:
  category: ct_resident
  notes: "CT 103 — Hermes Agent bot (Discord)"
```

The `host` field cross-references `hosts.yaml`. The validator enforces that every `host` value in `services.yaml` matches a key in `hosts.yaml`.

---

## 4. service.yaml — What Each Service Declares

Every service directory has a `service.yaml` file. This is how a service describes itself to humans, agents, and the validator. All 30 services have one.

### Fields

```yaml
name: homepage              # matches the directory name
kind: docker                # see kinds below
owner: homelab
deployable: true            # can the webhook deploy this?
managed_by: homelab         # who manages it
host_key: portainer-vm      # references inventory/hosts.yaml
compose_path: compose.yml
secrets: sops               # none | env | sops
healthcheck: https://homepage.yourdomain.com
risk_level: low             # low | medium | high | manual-only
data_paths: []              # host paths with persistent data
notes: "Config in-repo; API keys via .env.sops"
```

### risk_level — the most important field

`risk_level` is the single most important field for agents and humans making decisions about a service.

| Level | What it means | Examples |
|-------|--------------|---------|
| `low` | Stateless or easily replaceable. Redeploy is safe anytime. | homepage, dozzle, ash, beszel, tao |
| `medium` | Has persistent state or external dependencies. Redeploy with care. | ollama, filebrowser, opc, uptime-kuma, honcho |
| `high` | Data-bearing, hard to recover, or has downstream dependencies. | jellyfin, immich, gitea, wazuh, webhook |
| `manual-only` | Never deploy via automation. Human executes directly. | claude-ops, ai (GPU VM) |

The `high` and `manual-only` services are the ones that can cause real pain if something goes wrong. `immich` in particular contains your irreplaceable photo library — it gets extra-careful treatment.

### data_paths

This field lists host filesystem paths where the service stores persistent data. It's not enforced automatically — it's a signal to humans and agents: "if you redeploy this service, these paths are what's at risk."

```yaml
data_paths:
  - /mnt/media/immich/upload   # the actual photos, on the 4TB HDD
```

---

## 5. The .deploy File

The `.deploy` file in each service directory is what the webhook reads to figure out where and how to deploy that service. It's a simple key=value text file.

### Keys

| Key | Required | Default | Purpose |
|-----|----------|---------|---------|
| `HOST` | **yes** | — | Target host IP |
| `SSH_USER` | no | `root` | SSH login user |
| `REPO` | no | `/opt/homelab` | Remote path to the homelab git checkout |
| `BUILD` | no | `false` | Build from source instead of pulling images |
| `SOURCE_PATH` | no (yes if BUILD=true) | — | Path to source repo on the remote host |
| `COMPOSE_FILE` | no | `compose.yml` | Compose filename (used in non-standard REPO paths) |
| `GITEA_REPO` | no | — | Gitea repo to clone when BUILD=true |
| `GITHUB_REPO` | no | — | GitHub URL to clone when BUILD=true |

### Standard deploy (most services)

```
HOST=192.168.x.5
```

That's it. The webhook SSHs to VM 101, does `git pull` on the homelab checkout, and runs `docker compose up -d`.

### Non-standard deploy (GPU service)

```
HOST=192.168.x.167
SSH_USER=khris
REPO=/opt/gpu-compute
COMPOSE_FILE=docker-compose.yml
```

Here the compose files live at a non-standard path on the remote, so the webhook SCPs the compose file directly instead of relying on git pull.

### Build-from-source deploy

```
HOST=192.168.x.5
BUILD=true
SOURCE_PATH=/opt/opc
GITEA_REPO=your-gitea-user/opc
```

The webhook clones/pulls the source repo on the remote before running `docker compose up --build`.

---

## 6. Secrets Management

Secrets use **SOPS + age encryption**. The short version: secret files are encrypted in git, decrypted at deploy time.

### How it works

- The age private key lives at `/root/.age/key.txt` on CT 102 — **this key is never committed to git**
- The public key is in `.sops.yaml` at the repo root — this is how SOPS knows who can decrypt
- Any `.env` file that contains secrets is encrypted as `.env.sops` and committed to git
- At deploy time, the webhook decrypts `.env.sops` → `.env` and SCPs the plaintext `.env` to the target host, then removes the local copy

### Decrypt a secret manually

```bash
SOPS_AGE_KEY_FILE=/root/.age/key.txt sops --decrypt \
  --input-type dotenv --output-type dotenv \
  services/homepage/.env.sops
```

### Secrets files on CT 102

Credentials the ops scripts use directly live at `/root/.secrets/` on CT 102 (not in git). These are sourced by deploy scripts:

| File | Contents |
|------|---------|
| `/root/.secrets/opnsense` | OPNsense API key + secret |
| `/root/.secrets/npm` | NPM admin email + password |
| `/root/.secrets/portainer` | Portainer API credentials |
| `/root/.secrets/gitea` | Gitea token + URL |
| `/root/.secrets/gmail` | Gmail app password for patch notifications |

### What's encrypted vs. plaintext (and what needs fixing)

Ideally every service with secrets uses `.env.sops`. In practice, a few services still have plaintext `.env` files at runtime — this is a known gap:

- `immich` — DB credentials in plaintext `.env` (not SOPS)
- `gitea`, `wazuh`, `stable-diffusion` — plaintext `.env`
- `autoforge-ui`, `opc` — plaintext `.env` with API keys

These should be migrated to SOPS but haven't been yet.

---

## 7. The Validator (CI)

Every PR runs `python3 scripts/validate_inventory.py` automatically via Gitea CI. This script runs **13 checks** across the whole repo. A PR that fails CI cannot be merged.

### The 13 checks

1. **Schema conformance** — every entry in `hosts.yaml` and `services.yaml` matches its JSON schema
2. **Host cross-references** — every `host` field in `services.yaml` exists in `hosts.yaml`
3. **Host field required** — `compose_managed` and `special` services must have a `host` field
4. **Key parity** — every directory under `services/` has an entry in `services.yaml` and vice versa
5. **Category truth** — `compose_managed` means `.deploy` + `compose.yml` both exist on disk; `ct_resident` means no `.deploy` exists; etc.
6. **IP consistency** — the `host` IP in `services.yaml` matches the `HOST=` in the `.deploy` file
7. **Build flag consistency** — `build: true` in `services.yaml` ↔ `BUILD=true` in `.deploy` (both or neither)
8. **No duplicate keys** — no service name appears twice in `hosts.yaml` or `services.yaml`
9. **service.yaml schema** — every `service.yaml` validates against `service_file.schema.json`
10. **compose_path exists** — for deployable services, the `compose_path` file actually exists on disk
11. **.deploy content** — `HOST=` present, no unknown keys, `BUILD=true` requires `SOURCE_PATH`
12. **Doc sentinel freshness** — the auto-generated sections in `README.md` are up to date (matches what `gen_docs.py` would produce)
13. **No stale URLs** — `.md` files don't reference `.yourdomain.com` URLs that aren't registered in the inventory or known infrastructure

### Running it locally

```bash
python3 scripts/validate_inventory.py
# OK — 7 hosts, 30 services validated, 30 service.yaml files
```

You can run this any time before opening a PR to catch issues early.

---

## 8. Deploy Scripts and Safe Wrappers

### Per-service deploy.sh

Most service directories have a `deploy.sh`. These are **first-time setup scripts** — you run them once when you're adding a new service, to create the NPM proxy, Unbound DNS entry, SCP configs, etc. They are not run on every deploy (the webhook handles that).

For services where setup is trivial (just `docker compose up -d`), the deploy.sh is a 10-line script. For services that need NPM + DNS registration, it used to be 90 lines — now it's ~20 lines, because the common logic moved into the shared library.

### scripts/lib/deploy-helpers.sh

This is the shared library that all deploy scripts source. It provides six functions:

**`preflight_ssh <host>`**
Checks SSH connectivity to the target host before doing anything. If the host is unreachable, it exits immediately with a clear error rather than failing halfway through a deploy.

```bash
preflight_ssh "192.168.x.5"
```

**`require_secrets <file...>`**
Checks that secrets files exist before starting. Prevents cryptic errors when a secrets file is missing.

```bash
require_secrets /root/.secrets/npm /root/.secrets/opnsense
```

**`remote_compose_deploy <host> <remote_dir> <compose_src>`**
The standard pattern for deploying a compose service to a remote host: creates the remote directory, SCPs the compose file, runs `docker compose pull && docker compose up -d`.

```bash
remote_compose_deploy "192.168.x.5" "/opt/dozzle" "$SCRIPT_DIR/compose.yml"
```

**`npm_proxy_upsert <npm_url> <domain> <forward_host> <port> <cert_id>`**
Creates or updates an NPM reverse-proxy entry idempotently (skips creation if it already exists). Requires `$NPM_EMAIL` and `$NPM_PASSWORD` from sourcing `/root/.secrets/npm`.

**`unbound_dns_upsert <opnsense_url> <hostname> <domain> <target_ip> <description>`**
Adds an OPNsense Unbound DNS override idempotently (skips if already present). Requires `$OPN_KEY` and `$OPN_SECRET` from sourcing `/root/.secrets/opnsense`.

**`wait_for_http <url> <tries> <interval_sec> <label>`**
Polls a URL until it returns HTTP 2xx, printing attempt progress. Used after deploy to confirm a service came up.

```bash
wait_for_http "http://192.168.x.48:3010/api/v1/version" 15 3 "Gitea"
```

### Using the library in a deploy script

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../../scripts/lib/deploy-helpers.sh"

HOST="192.168.x.5"
preflight_ssh "$HOST"
remote_compose_deploy "$HOST" "/opt/myservice" "$SCRIPT_DIR/compose.yml"
echo "Done."
```

---

## 9. The Agent Ecosystem

Several AI agents live in or interact with this homelab. Here's who they are and what authority they have.

| Agent | Host | Model | Role | Can merge PRs? | Can run deploys? |
|-------|------|-------|------|---------------|-----------------|
| **Claude** (you're reading this) | CT 102 | Claude Sonnet | GitOps controller, dev, architecture | Yes, on human instruction | Yes, on human instruction |
| **Khris** | CT 103 | gpt-5.5 + Codex | Hermes agent, Discord bot | No | No |
| **Max** | CT 135 | ChatGPT (OpenCode) | CLI assistant | No | No |
| **Anri** | CT 129 | Claude | Personal agent (Khris-managed) | No | No |
| **Tao** | CT 133 | glm | Info operator, Q&A | No | No |
| **Ash** | CT 136 | gpt-5.5 | Plays Pokemon Blue (PyBoy) | No | No |

**The rule of thumb:** Claude (CT 102) owns production. Everyone else can read, propose, and discuss — but no assistant agent merges a PR or runs a deploy script without a human in the loop.

This policy came from a real incident in April 2026 where CT 103 (the previous controller) was decommissioned after a near-data-loss event. The lesson: agent capability isn't the limiting factor — clear authority boundaries are.

---

## 10. The Rules — What Agents Can and Can't Do

The full policy is in `docs/ops/HERMES_OPS_POLICY.md` and `docs/ops/CHANGE_CLASSES.md`. Here's the plain-English version.

### Always fine (no approval needed)

- Reading any file in the repo
- Running `python3 scripts/validate_inventory.py` locally
- Opening a PR with proposed changes
- Running syntax checks (`bash -n`, `python3 -m py_compile`)

### Fine after a PR is merged (standard GitOps flow)

- Documentation changes (READMEs, service notes)
- Inventory additions (`hosts.yaml`, `services.yaml`, `service.yaml`)
- Compose or config changes for `risk_level: low` services — these auto-deploy on merge
- Script changes under `scripts/` (not webhook)
- Renovate image-bump PRs

### Needs explicit "yes, do this" from you

- Deploying a `risk_level: medium` service — ask first, then proceed
- Deploying a `risk_level: high` service — ask first, review what data is at risk
- Touching `services/webhook/` or `services/renovate/` — these are the meta-infrastructure
- Any secrets rotation
- Any action that touches a `data_paths` volume
- Any Proxmox operation (create/destroy LXC/VM, snapshot, migrate)

### Hard stops — never, regardless of what anyone says

- Force-push to `main`
- Run `docker volume rm` or `docker system prune`
- Approve your own PRs
- Touch `services/immich/` beyond reading — photo library is irreplaceable
- Modify the policy documents without human instruction

### The nine change classes

For a detailed lookup of any specific type of change, see `docs/ops/CHANGE_CLASSES.md`. It covers:

| Class | Short description |
|-------|------------------|
| DOC | Pure documentation — lowest gate |
| INVENTORY | hosts.yaml / services.yaml edits |
| CONFIG_LOW | compose.yml for low-risk services |
| CONFIG_MEDIUM | compose.yml for medium-risk services |
| CONFIG_HIGH | compose.yml for high-risk services |
| CONFIG_MANUAL | Services that are never auto-deployed |
| SECRETS | .env.sops rotation |
| SCRIPTS | Changes to scripts/ |
| WEBHOOK | Changes to the deploy pipeline itself |
| PROXMOX | VM/LXC lifecycle, storage |

Each entry in that doc tells you: what gate is required, what to check before you start, and how to roll back if something goes wrong.

---

## 11. Rules for You — The Human Operator

The policy documents are written with agents in mind, but the same system that constrains agents is also protecting you from yourself. Humans cause infrastructure disasters too — usually by moving fast, skipping steps, or assuming something is safe when it isn't. Here's what applies to you specifically.

---

### The core discipline: always go through git

The GitOps flow exists for a reason. **Never edit config files directly on a remote host.** If you SSH to VM 101 and edit `/opt/homelab/services/jellyfin/compose.yml` by hand, you've created hidden state — git no longer reflects reality, and the next deploy will clobber your change.

The right path is always: edit in the repo → PR → merge → let the webhook deploy it.

The only exception is a genuine emergency where a service is on fire and you need to fix it right now. In that case: fix it directly, then immediately open a PR that matches what you did so git catches up.

---

### Do's

**Do run the validator before opening a PR.**
```bash
python3 scripts/validate_inventory.py
```
It catches things you'd never notice manually — stale URLs, mismatched IPs, missing fields. Takes two seconds.

**Do read CI output before merging.**
CI failing means something is wrong. Don't merge a red PR just because the change looks small. The validator is designed to catch subtle inconsistencies that don't look like bugs.

**Do check `data_paths` in `service.yaml` before redeploying a medium/high service.**
Know what's on disk that could be affected. If a service has `/mnt/media/immich/upload` in its `data_paths`, that's your photo library. Think before you touch it.

**Do confirm the T7 is mounted before any backup-dependent operation.**
```bash
ssh root@192.168.x.4 'mountpoint -q /mnt/backup && echo mounted || echo NOT MOUNTED'
```
Proxmox backups run every Sunday at 2AM. If the T7 isn't mounted, backups silently fail.

**Do keep the age key backed up.**
The SOPS age private key lives at `/root/.age/key.txt` on CT 102. If CT 102 is destroyed and this key isn't backed up, every `.env.sops` in the repo is unrecoverable. The DR doc at `docs/DR.md` covers how to back it up. Do this.

**Do review Renovate PRs before merging, especially for high-risk services.**
Renovate opens PRs automatically when image versions change. Most are safe. But a Gitea major version bump or a Wazuh update deserves a look at the upstream changelog before you hit merge.

---

### Don'ts

**Don't run `docker compose down -v`.**
The `-v` flag destroys named volumes. For Jellyfin or Immich, that means your config and media database are gone. `docker compose up -d` is safe. `docker compose down` (no `-v`) is safe. `docker compose down -v` is almost never what you want.

**Don't run `docker system prune` on VM 101 without checking what's running.**
Prune removes stopped containers, dangling images, and unused networks. It seems harmless until it removes a volume that was unmounted but not deleted. Use `docker system prune` only, never `docker system prune --volumes`.

**Don't merge PRs that touch `services/webhook/` or `services/renovate/` casually.**
Webhook is the GitOps pipeline. Breaking it means no service can deploy until you fix it manually. Renovate is the dependency updater. These two services are load-bearing infrastructure — treat them like production plumbing.

**Don't force-push to main.**
Ever. If the commit history has a problem, open a revert PR. Gitea has branch protection on `main` — don't disable it.

**Don't SSH to CT 102 and restart Docker arbitrarily.**
CT 102 runs the webhook, Renovate, auth-proxy, and Beszel agent. Restarting Docker on CT 102 disrupts all of these. If you need to restart a single service, use `docker compose restart` in its directory.

**Don't touch immich volumes.**
`/mnt/media/immich/upload` on VM 101 is your photo library on the 4TB HDD. No prune, no rm, no recreate without a verified backup. The Immich DB credentials are also in a plaintext `.env` (not SOPS), so rotation is a manual, careful operation.

**Don't restart or destroy CT 102 without planning.**
CT 102 is the GitOps controller. If it's down, the webhook is down, and no deploys happen until it's back. It's backed up by Proxmox weekly, but recovery takes time. Treat it like the most important machine in the lab.

---

### The "never" list (same as for agents)

These apply to you too, not just AI assistants:

- No force-push to `main`
- No `docker volume rm` on production volumes
- No approving your own PRs without reading the diff
- No destructive Proxmox ops (destroy, volume delete) without a confirmed recent backup
- No secrets committed to git in plaintext

---

### Specific per-service gotchas

| Service | Watch out for |
|---------|--------------|
| **immich** | Plaintext `.env` (not SOPS). Photo library at `/mnt/media/immich/upload`. Never `down -v`. |
| **jellyfin** | DB encryption key lives in the Portainer env var — if you recreate the container and lose this, the library DB is unreadable. Document it before touching. |
| **gitea** | Postgres data at `/opt/gitea/data/` on CT 123. All your code lives here. Back up before major upgrades. |
| **webhook** | If you change `webhook-handler.sh` and it breaks, GitOps stops. Test changes in a side file before replacing the live one. |
| **wazuh** | Takes 2–3 minutes to start. Don't assume it's broken after a restart — `wait_for_http` in the deploy script polls for 6 minutes. |
| **portainer** | Runs on VM 101 :9443. If Portainer is down, the Portainer API calls in other deploy scripts fail. Don't take it down casually. |
| **renovate** | Runs on a schedule. If it's failing silently, you'll stop getting image-bump PRs. Check Gitea notifications occasionally. |

---

### When it's OK to bypass the GitOps flow

Emergency only. If a service is actively broken and needs a hotfix right now:

1. Fix it directly on the host via SSH
2. Note exactly what you changed
3. Immediately open a PR that makes the repo match what you did
4. Merge the PR — the next webhook fire will be a no-op (service is already in the right state)

Never let a direct-edit stay unreflected in git for more than a few hours. The longer you wait, the more likely the next routine deploy clobbers your fix.

---

## 12. Common Tasks

### Add a new service

```bash
# 1. Scaffold the service directory
scripts/new-service.sh myservice

# 2. Fill in the generated files:
#    services/myservice/compose.yml    — the Docker Compose definition
#    services/myservice/.deploy        — at minimum: HOST=<ip>
#    services/myservice/service.yaml   — fill in all fields, especially risk_level
#    services/myservice/.env.example   — if it needs secrets

# 3. Validate locally
python3 scripts/validate_inventory.py

# 4. Open a PR
```

### Redeploy a service (after a PR merges)

Nothing to do — the webhook fires automatically. Check `/var/log/deploy.log` on CT 102 to confirm.

### Force-redeploy a service without a PR

Touch any file in the service directory, commit, and merge. Or run the deploy script manually from CT 102:

```bash
cd /opt/homelab/services/myservice
bash deploy.sh
```

### Rotate a secret

```bash
# 1. Edit the plaintext .env locally
# 2. Re-encrypt with SOPS
SOPS_AGE_KEY_FILE=/root/.age/key.txt sops --encrypt \
  --input-type dotenv --output-type dotenv \
  services/myservice/.env > services/myservice/.env.sops

# 3. Open a PR — webhook decrypts and deploys on merge
```

### Check what's deployed vs. what's in git

```bash
# On CT 102
cd /opt/homelab && git log --oneline -10
# Compare to what's running
ssh root@192.168.x.5 'docker ps --format "{{.Names}}\t{{.Image}}"'
```

### Validate the whole repo

```bash
python3 scripts/validate_inventory.py
# OK — 7 hosts, 30 services validated, 30 service.yaml files
```

### See deploy logs

```bash
tail -f /var/log/deploy.log
```

---

## Appendix: What We Built (PRs 1–9)

The maintainability initiative ran from late April to May 2026. Here's what each phase added:

| PR | What it did |
|----|------------|
| 1 | Fixed doc drift, stale references, broken CI URLs — baseline cleanup |
| 2 | Created `inventory/hosts.yaml` + `inventory/services.yaml` with JSON schemas + validator (checks 1–8) |
| 3 | Added `service.yaml` to 8 pilot services + `service_file.schema.json` + validator checks 9–10 |
| 3b | Added `service.yaml` to the remaining 21 services |
| 4 | Normalized all `.deploy` files (trailing newlines, `HOST=` required); validator check 11; full `.deploy` key reference in CLAUDE.md |
| 5 | `scripts/gen_docs.py` — auto-generates the services table and repo structure in README.md; `display_name` field; validator check 12 |
| 6 | Fixed `new-service.sh` (was broken in 4 ways); validator check 13 (stale URL scanner); fixed 8 stale refs |
| 7 | CI job: runs `validate_inventory.py` (all 13 checks) automatically on every PR |
| 8 | `scripts/lib/deploy-helpers.sh` — 6 shared functions; 12 service deploy scripts refactored |
| 9 | `HERMES_OPS_POLICY.md` rewrite (removed all `[future]` stubs) + new `CHANGE_CLASSES.md` |

Before this work: the repo had hidden state, inconsistent deploy patterns, no automated validation, and agents could cause real damage by acting on stale or ambiguous information. After: one source of truth, 13 automated checks on every PR, explicit risk classifications for all 30 services, and a clear policy document that any agent (or human) can open to know exactly what they're allowed to do.
