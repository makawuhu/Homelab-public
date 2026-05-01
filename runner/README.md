# Deploy Runner — Phase 0

This directory contains the host-local deploy runner and its supporting files.

## Files

| File | Purpose |
|------|---------|
| `RUNNER_CONTRACT.md` | Runner responsibilities, boundaries, and contract |
| `deploy-runner` | Shell script — the runner itself |
| `deploy-runner@.service` | Systemd template unit |
| `trigger-runner` | SSH trigger wrapper (called by coordinator) |
| `configs/` | Per-service YAML configs per host |
| `FAILURE_TEST_PLAN.md` | Controlled failure tests before going active |

## Architecture

```
Git Merge → Webhook → Coordinator (CT 102) → SSH trigger → Host Runner → Local Deploy
```

- **Coordinator** = existing deploy.sh on CT 102 (webhook detection + host mapping)
- **Runner** = shell script, systemd oneshot, per-service execution
- **Trigger** = `ssh <host> systemctl start deploy-runner@<service>`

## Installation on Target Host

```bash
# Copy runner script
cp deploy-runner /usr/local/bin/deploy-runner
chmod +x /usr/local/bin/deploy-runner

# Copy systemd unit
cp deploy-runner@.service /etc/systemd/system/
systemctl daemon-reload

# Create config and log directories
mkdir -p /etc/deploy-runner /var/log/deploy-runner /var/lib/deploy-runner

# Copy service config
cp configs/<service>.<host>.yaml /etc/deploy-runner/<service>.yaml
chmod 600 /etc/deploy-runner/<service>.yaml
```

## Triggering from Coordinator

```bash
# From CT 102
bash trigger-runner 192.168.x.5 dozzle
# Or with specific revision
bash trigger-runner 192.168.x.5 dozzle abc1234
```

## Shadow Mode

Service configs have `shadow: true` by default during pilot.
The runner logs what it would do without executing.

Flip to active: set `shadow: false` in the service config.

## Monitoring

- Runner touches `/var/lib/deploy-runner/heartbeat` on each run
- Uptime Kuma push monitor checks heartbeat staleness
- Result JSON files in `/var/log/deploy-runner/`
- Journal: `journalctl -u deploy-runner@dozzle`