# Service Contract

Every directory under `services/<name>/` should conform to this contract. This document defines the target state; rollout happens incrementally across PRs 2–4.

> **Status:** Contract defined here in PR 1. `service.yaml` rollout begins in PR 3.
> `inventory/` and the scripts referenced below do not exist yet — they are created in PRs 2 and 6.
> Until those PRs land, use this document as the design spec, not operational truth.

---

## Required files by service kind (target state)

| File | `docker` | `lxc-external` | `vm-doc` | `doc-only` |
|---|---|---|---|---|
| `README.md` | required | required | required | required |
| `service.yaml` | required | required | required | required |
| `compose.yml` | required | — | — | — |
| `.deploy` | required | — | — | — |
| `.env.example` | if env vars exist | — | — | — |

> `service.yaml` does not exist in any service directory yet. It will be added starting in PR 3.

---

## `service.yaml` field reference (target schema)

```yaml
name: <string>               # matches directory name under services/
kind: <enum>                 # see kinds below
owner: <string>              # team or person responsible
deployable: <bool>           # true if GitOps webhook can deploy this
managed_by: <enum>           # homelab | external | manual | deprecated
host_key: <string>           # references a key in inventory/hosts.yaml
compose_path: <string>       # relative path to compose.yml (if deployable)
secrets: <enum>              # none | env | sops
healthcheck: <string|null>   # URL or null
risk_level: <enum>           # low | medium | high | manual-only
data_paths: <list|null>      # host paths with persistent data
notes: <string|null>         # anything an agent needs to know that isn't obvious
```

> `inventory/hosts.yaml` does not exist yet. It will be created in PR 2.

---

## Service kinds

| Kind | Description |
|---|---|
| `docker` | Compose-managed container deployed via GitOps webhook |
| `lxc-external` | LXC documented here but managed externally (e.g. Khris-managed) |
| `vm-doc` | VM documented here; not deployed via this repo |
| `doc-only` | Documentation-only entry; no deployable artifact |
| `special` | Requires custom deploy logic; see `notes` in `service.yaml` |
| `deprecated` | No longer active; kept for reference |

---

## Risk levels

| Level | Meaning |
|---|---|
| `low` | Stateless or easily replaceable; redeploy is safe |
| `medium` | Has persistent state or external dependencies; redeploy with care |
| `high` | Data-bearing, hard to recover, or has downstream dependencies |
| `manual-only` | Never deploy via automation; human must execute directly |

---

## `.deploy` file format

Used by the GitOps webhook (`services/webhook/scripts/webhook-handler.sh`) to determine where and how to deploy a service. **This is the current operational format — it exists today.**

```
HOST=<ip>                     # required — target host IP
SSH_USER=<user>               # optional, default: root
REPO=<path>                   # optional, default: /opt/homelab
BUILD=<true|false>            # optional, default: false
SOURCE_PATH=<path>            # required if BUILD=true
GITEA_REPO=<org/repo>         # optional — clone from internal Gitea
GITHUB_REPO=<url>             # optional — clone from GitHub
COMPOSE_FILE=<filename>       # optional, default: compose.yml
```

All keys must be in `KEY=value` format — one per line, no spaces around `=`. The webhook parses with `grep '^HOST='`. Any script that reads `.deploy` must use the same parsing pattern, not `cat`.

---

## Adding a new service (target process — not fully automated yet)

1. Create `services/<name>/` with required files per the table above.
2. Add `service.yaml` with all required fields. *(PR 3+ only)*
3. Add entry to `inventory/services.yaml`. *(PR 2+ only)*
4. Run `python3 scripts/validate_inventory.py` — must pass. *(PR 2+ only)*
5. Run `python3 scripts/generate_docs.py` — regenerate README/CLAUDE.md sections. *(PR 5+ only)*
6. Open a PR.

Until inventory and scripts exist, steps 2–5 are skipped. Add `README.md`, `compose.yml`, `.deploy`, and `.env.example` and open the PR directly.
