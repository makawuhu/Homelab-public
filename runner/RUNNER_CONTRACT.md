# Runner Contract — Host-Local Deploy Runner v1

## Purpose

A host-local runner applies approved Git-driven deployments on its assigned host.
It does not plan, it does not cross-host, it does not decide what to deploy.
It executes what the coordinator tells it to and reports the result.

## Responsibilities

1. Receive deployment signal from coordinator (via SSH trigger)
2. Validate the assigned service(s) changed in the target revision
3. Pull repo to target revision locally
4. Decrypt host-local secrets (SOPS + age)
5. Execute local deploy command
6. Run post-deploy health check
7. Report success or failure with evidence
8. On failure: stop and alert (no retry, no blind rollback)
9. Expose heartbeat for monitoring

## What the Runner Does NOT Do

- Does not access other hosts
- Does not manage global secrets
- Does not modify DNS, NPM, or Proxmox
- Does not plan deployments or decide what to deploy
- Does not auto-retry or auto-rollback (unless explicitly configured per-service)
- Does not update itself (separate lifecycle)

## Signaling Protocol

The coordinator triggers the runner via SSH:

```
ssh <host> "sudo systemctl start deploy-runner@<service>"
```

This runs a systemd oneshot service that:
1. Reads the service config
2. Executes the deploy
3. Reports result
4. Exits

No long-running daemon. No open ports. No webhook listeners.

## Configuration Schema

Per-service YAML config at `/etc/deploy-runner/<service>.yaml`:

```yaml
service: dozzle
repo_path: /opt/homelab
compose_path: services/dozzle/compose.yml
deploy_command: "docker compose up -d --remove-orphans"
health_check: "curl -sf http://localhost:8888/"
health_timeout: 30
rollback_allowed: true
secrets:
  - path: services/dozzle/.env.sops
    target: services/dozzle/.env
    encrypted: true
```

## Reporting Format

Each run writes a JSON result to `/var/log/deploy-runner/<service>-<timestamp>.json`:

```json
{
  "service": "dozzle",
  "host": "vm101",
  "revision": "abc1234",
  "timestamp": "2026-04-19T03:00:00Z",
  "status": "success|failure|shadow",
  "health_check": "pass|fail|skip",
  "duration_seconds": 12,
  "output": "last 50 lines of deploy output",
  "error": "error message if failure"
}
```

## Failure Policy

- Default: **stop and alert**
- Stateless services with `rollback_allowed: true` may auto-rollback to previous revision
- Stateful services: **never auto-rollback** unless explicitly engineered
- No infinite retry
- Alert via Uptime Kuma push monitor

## Shadow Mode

When the runner config has `shadow: true`, it:
1. Computes what it would do
2. Logs the planned actions
3. Does NOT execute the deploy
4. Reports as `status: shadow`

This allows validation without risk.

## Heartbeat

Each successful or failed run touches a timestamp file:
`/var/lib/deploy-runner/heartbeat`

Uptime Kuma push monitor checks this file hasn't gone stale.

## Security

- Runner runs as root (needs Docker + SOPS access)
- No network listeners
- Triggered only via SSH from coordinator (CT 102)
- Service configs are root-owned, mode 600
- SOPS age key at `/root/.age/key.txt` (existing)