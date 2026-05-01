# Change Classes

A lookup table for agents deciding what type of change they are making and what gate it requires. Before proposing or executing any change, identify its class here.

---

## Quick reference

| Class | Examples | Gate | Auto-deploy on merge? |
|-------|----------|------|-----------------------|
| [DOC](#doc) | README, service notes, policy docs | PR + CI | No |
| [INVENTORY](#inventory) | Add/remove host or service entry | PR + CI | No |
| [CONFIG_LOW](#config_low) | compose.yml for `risk_level: low` service | PR + CI | Yes |
| [CONFIG_MEDIUM](#config_medium) | compose.yml for `risk_level: medium` service | PR + CI + explicit confirm | Yes |
| [CONFIG_HIGH](#config_high) | compose.yml for `risk_level: high` service | PR + CI + explicit confirm + manual deploy | Manual |
| [CONFIG_MANUAL](#config_manual) | Any `risk_level: manual-only` service | Explicit instruction + human executes | Never automated |
| [SECRETS](#secrets) | `.env.sops`, `secrets/*.sops` rotation | Explicit instruction + PR | Yes (decrypt at deploy) |
| [SCRIPTS](#scripts) | `scripts/` validators, deploy helpers | PR + CI + human review | No |
| [WEBHOOK](#webhook) | `services/webhook/` or `services/renovate/` | Explicit instruction + PR | Manual |
| [PROXMOX](#proxmox) | VM/LXC lifecycle, storage, snapshots | Explicit instruction, human confirms | Never automated |

---

## DOC

**What:** Changes to documentation only — `README.md`, `service.yaml` `notes` field, `docs/` files, comments in scripts. No functional change.

**Gate:** PR + CI pass.

**Pre-checks:**
```bash
python3 scripts/validate_inventory.py   # must pass
python3 scripts/gen_docs.py --check     # no sentinel drift
```

**Rollback:** `git revert <sha>` + open new PR.

**Examples:**
- Fix a typo in a service README
- Update `notes:` in a `service.yaml`
- Add a new entry to `docs/ops/`

---

## INVENTORY

**What:** Changes to `inventory/hosts.yaml` or `inventory/services.yaml` — adding, removing, or updating host/service entries.

**Gate:** PR + CI pass (validator enforces schema and cross-references).

**Pre-checks:**
```bash
python3 scripts/validate_inventory.py   # must pass
```

**Rollback:** `git revert <sha>` + open new PR.

**Examples:**
- Add a new host after provisioning a new LXC
- Update a service's `host_key` after migration
- Deprecate a decommissioned service

---

## CONFIG_LOW

**What:** `compose.yml` or `.deploy` change for a service where `service.yaml` has `risk_level: low`.

**Current `low` services:** anri, ash, beszel, coolercontrol, dozzle, homelab-assistant, homepage, khris, max, nature-forge-ui, renovate, studio, tao

**Gate:** PR + CI pass. Merge triggers automatic webhook deploy — no additional confirmation needed.

**Pre-checks:**
```bash
python3 scripts/validate_inventory.py   # must pass
bash -n services/<name>/deploy.sh       # if touching deploy.sh
```

**Post-deploy verify:** Check `service.yaml` `healthcheck` URL responds.

**Rollback:** `git revert <sha>` + open new PR → auto-redeploy on merge.

---

## CONFIG_MEDIUM

**What:** `compose.yml` or `.deploy` change for a service where `service.yaml` has `risk_level: medium`.

**Current `medium` services:** autoforge-ui, filebrowser, gpu, honcho, ollama, ollama-gpu, opc, stable-diffusion, uptime-kuma

**Gate:** PR + CI pass + **explicit human confirmation before merging**. Ask: "This service has `risk_level: medium` — okay to merge and auto-deploy?"

Merge triggers automatic webhook deploy.

**Pre-checks:**
```bash
python3 scripts/validate_inventory.py
```

**Post-deploy verify:** Check healthcheck URL. Confirm service logs look clean.

**Rollback:** `git revert <sha>` + open new PR → auto-redeploy. For stateful services, check that persistent volumes are intact before declaring success.

---

## CONFIG_HIGH

**What:** `compose.yml` or `.deploy` change for a service where `service.yaml` has `risk_level: high`.

**Current `high` services:** gitea, immich, jellyfin, portainer, wazuh, webhook

**Gate:** PR + CI pass + **explicit human confirmation** + **human reviews data impact** before merge. Even after merge, the webhook auto-deploys — but the human must confirm they've assessed the risk.

**Before proposing the PR, state:**
- What data paths are affected (check `data_paths` in `service.yaml`)
- Whether the change requires downtime
- Whether config or volume state could be affected

**Post-deploy verify:** Check healthcheck. Verify data-bearing paths are still accessible.

**Rollback:** More complex — may require restoring from backup if volumes were affected. Do not rollback without understanding what state the service is in.

---

## CONFIG_MANUAL

**What:** Any change to a service where `service.yaml` has `risk_level: manual-only`.

**Current `manual-only` services:** ai, claude-ops

**Gate:** Explicit human instruction. The agent may propose a PR, but **the human runs `deploy.sh` directly** — never the agent.

**Why:** These services control the operations infrastructure itself (`claude-ops`) or are one-of-a-kind GPU VMs (`ai`) where automated redeploy carries unacceptable risk.

---

## SECRETS

**What:** Rotating, re-encrypting, or adding secrets — `.env.sops` files or `secrets/*.sops`.

**Gate:** Explicit human instruction + PR. The agent may prepare the encrypted file, but the human confirms the rotation before merging.

**Pre-checks:**
- Confirm the new secret is valid before encrypting
- Confirm the old secret is no longer needed or has been rotated at the source

**Decrypt for verification:**
```bash
SOPS_AGE_KEY_FILE=/root/.age/key.txt sops --decrypt \
  --input-type dotenv --output-type dotenv services/<name>/.env.sops
```

**Rollback:** Restore old `.env.sops` from git + redeploy. Note: the secret at the source (API key, password) may need to be rolled back separately.

---

## SCRIPTS

**What:** Changes to scripts under `scripts/` — validators, deploy helpers, patching scripts, gen_docs.

**Gate:** PR + CI pass + human review of the diff. Script changes are not auto-deployed; they take effect next time the script runs.

**Pre-checks:**
```bash
bash -n scripts/<name>.sh               # syntax check
python3 -m py_compile scripts/<name>.py # for Python scripts
python3 scripts/validate_inventory.py   # must still pass
```

**Rollback:** `git revert <sha>` + open new PR.

---

## WEBHOOK

**What:** Changes to `services/webhook/` (the GitOps deploy pipeline) or `services/renovate/` (the dependency update pipeline).

**Gate:** Explicit human instruction + PR. These services are the meta-infrastructure — a broken webhook stops all GitOps deploys.

**Before proposing:** State exactly what behavior changes, what the failure mode is if the change is wrong, and how to verify it works after merge.

**Post-deploy verify:** Trigger a test deploy (touch a low-risk service compose) and confirm the webhook fires correctly.

**Rollback:** Manual — SSH to CT 102 and revert the script directly if the webhook is broken and can't self-redeploy.

---

## PROXMOX

**What:** Any Proxmox-level operation — create/destroy LXC or VM, snapshot, resize storage, migrate, change passthrough.

**Gate:** Explicit human instruction, human confirms before execution. Agent does not SSH to Proxmox and run `pct` or `qm` commands unless directly told to.

**These actions are never triggered by a PR merge.** They are always executed interactively.

**Examples:**
- `pct create` / `pct destroy`
- `qm snapshot` / `qm rollback`
- Resizing a pool or adding a disk
- Changing PCI passthrough configuration

**Rollback:** Depends entirely on the operation. Destructive Proxmox ops (destroy, volume delete) may have no rollback path. Confirm backups exist before proceeding.
