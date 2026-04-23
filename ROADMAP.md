# Homelab Roadmap

## In Progress

## Planned

### 0. Multi-Host Container Update Monitoring ✅ COMPLETE

**Goal:** Know when images are outdated across all Docker hosts — not just VM 101.

Resolved via Renovate (CT 102). Renovate scans all `compose.yml` in the repo and opens PRs for outdated images. WUD and the old monitoring stack (Prometheus, Grafana, cAdvisor) have been decommissioned; Beszel is now the monitoring stack at beszel.yourdomain.com.

---

### 1. Disaster Recovery — Tier 1 (Config + Secrets)
**Goal:** Recover Proxmox from bare metal without losing config or secrets.

- [ ] Script to dump `/etc/pve/` and commit sanitized copy to git on a schedule
- [ ] Document GPU passthrough, bridge, and ZFS pool setup (hardware-specific config)
- [x] Secrets recovery doc — `docs/DR.md` covers age key backup and full reconstruction procedure
- [ ] Add `proxmox/restore.sh` — recreates ZFS pools, restores VMs/LXCs from T7 backups

### 2. Patch Management ✅
**Goal:** Know when containers update and when host/LXC OS patches are available — and apply them automatically where safe.

- [x] Gmail App Password + SMTP credentials in `/root/.secrets/gmail`
- [x] Watchtower: email notifications on container auto-update
- [x] WUD: SMTP trigger — email on new image version detected
- [x] `scripts/patching/orchestrate.sh` — weekly cron (Sundays 8am): auto-applies safe patches, opens Gitea PR for risky ones (kernel, docker minor+, systemd, libc6, PVE host)
- [x] `scripts/patch-policy.yml` — per-package classification rules with semver constraints
- [x] Gitea PR → webhook → apply loop validated end-to-end (PR #24, CT 124 bind9 packages)
- [x] All hosts covered: PVE + CT 102/104/122/123/125/129/132/133 + VM 131/134

### 3. Disaster Recovery — Tier 2 (Offsite)
**Goal:** Survive physical loss of the T7 drive.

- [ ] Choose offsite target (Backblaze B2 recommended — cheap, S3-compatible)
- [ ] Set up rclone with B2 credentials
- [ ] Post-vzdump hook: rclone sync `/mnt/backup` → B2 bucket
- [ ] Retention policy on B2 (match local: 4 weekly)
- [ ] Uptime Kuma monitor for last successful offsite sync

### 4. Firewall Management
**Goal:** OPNsense config in git; basic rule visibility.

- [ ] OPNsense config export via API → encrypted commit to git (weekly cron)
- [ ] Document current firewall rules in `network/opnsense/rules.md`
- [ ] API-driven rule management (add/remove rules via claude-ops)
- [ ] Alert on OPNsense firmware/package updates available

### 5. Secrets Encryption at Rest (SOPS + age) ✅ COMPLETE
**Goal:** Encrypt `.secrets/` and `.env` files so they're safe to include in backups and optionally git.

- [x] Generate age keypair at `/root/.age/key.txt`; public key in `.sops.yaml`
- [x] Encrypt `/root/.secrets/*` into `secrets/*.sops` in git
- [x] Encrypt service `.env` files into `services/*/.env.sops` in git
- [x] `deploy.sh` decrypts `.env.sops` → `.env` at deploy time, SCPs to target host
- [x] Patching scripts (`notify.sh`, `gitea-pr.sh`) read from sops
- [x] DR recovery procedure documented in `docs/DR.md`

### 6. Disaster Recovery — Validation
**Goal:** Prove the DR plan actually works.

- [ ] Test restore: pick a stopped VM/LXC, restore from T7 backup to a new ID
- [ ] Document actual recovery time
- [ ] DR runbook: `proxmox/DR_RUNBOOK.md` — bare metal to fully running homelab

### 8. Vulnerability Scanning (Wazuh + KEV/CVE)
**Goal:** Deploy Wazuh to provide automated CVE/KEV vulnerability detection across the homelab.

- [x] Deploy Wazuh server — CT 122 (`wazuh`, 192.168.x.47)
- [x] Wazuh stack deployed (manager + indexer + dashboard) — accessible at https://wazuh.yourdomain.com
- [x] Enroll agents on production hosts
- [x] Expose Wazuh API at `https://192.168.x.47:55000`
- [x] Add Wazuh dashboard to NPM + DNS
- [ ] Enable Wazuh vulnerability detection module on manager (cross-references CISA KEV + NVD)
- [ ] Create `wazuh_analyst` dashboard accounts for team members

---

### 9. claude-ops Succession — Transition to Khris (CT 103) ↩️ REVERSED 2026-04-22

CT 103 (khris/openclaw) was decommissioned on 2026-04-22 after a data drive incident. CT 102 (claude-ops) was reprovisioned and restored as the primary GitOps controller. Webhook and Renovate returned to CT 102.

- [x] Khris (CT 103) promoted to primary GitOps controller (2026-04-19)
- [x] Webhook deploy pipeline migrated CT 102 → CT 103 (port 9001) (2026-04-19)
- [↩] CT 103 decommissioned 2026-04-22 — webhook + Renovate returned to CT 102 (port 9000)
- [x] CT 102 reprovisioned as primary ops node; all secrets and repo restored

---

## Completed

- [x] **claude-ops-sandbox (CT 119) — DECOMMISSIONED 2026-04-11** — superseded by Khris (CT 103).
- [x] **khris (CT 103) — DECOMMISSIONED 2026-04-22** — webhook + Renovate returned to CT 102.
- [x] **GitOps remote deploy via webhook** — webhook on CT 102 (port 9000). `.deploy` file per service declares `HOST=<ip>`; merge to main auto-deploys changed services.
- [x] **Scheduled health checks** — Daily infra health check via claude-ops cron.
- [x] Monitoring stack (Prometheus, Grafana, cAdvisor, node-exporter, WUD) — decommissioned, replaced by Beszel at beszel.yourdomain.com
- [x] Weekly vzdump backups to Samsung T7 (`usb-backup`) — Sundays 2AM
- [x] T7 mount monitoring via Uptime Kuma push monitor
- [x] Uptime Kuma monitors fixed to use direct IPs (not domain names)
- [x] All service configs in git (Gitea `your-gitea-user/homelab`)
- [x] Auth proxy deployed (decommissioned with CT 102)
- [x] SOPS + age secrets encryption at rest