# OPNsense

**Host:** `192.168.x.1`
**Role:** Firewall, router, gateway, internal DNS (Unbound)
**Remote access:** Tailscale runs on OPNsense — provides VPN access to the entire `192.168.x.0/24` network

## API Access

API credentials for `claude-ops` are stored at `/root/.secrets/opnsense` on CT 102.

```bash
source /root/.secrets/opnsense   # sets OPN_KEY and OPN_SECRET
```

### Unbound DNS (host overrides)

All `*.yourdomain.com` entries point to NPM (`192.168.x.31`) except where noted.

```bash
# List host overrides
curl -sk -u "$OPN_KEY:$OPN_SECRET" \
  https://192.168.x.1/api/unbound/settings/searchHostOverride

# Add override
curl -sk -u "$OPN_KEY:$OPN_SECRET" \
  -X POST https://192.168.x.1/api/unbound/settings/addHostOverride \
  -H "Content-Type: application/json" \
  -d '{"host": {"hostname": "myservice", "domain": "yourdomain.com", "server": "192.168.x.31", "description": ""}}'

# Apply changes (required after add/delete)
curl -sk -u "$OPN_KEY:$OPN_SECRET" \
  -X POST https://192.168.x.1/api/unbound/service/reconfigure \
  -H "Content-Type: application/json" -d '{}'
```

### Firmware / package updates

```bash
# Check for available updates
curl -sk -u "$OPN_KEY:$OPN_SECRET" \
  https://192.168.x.1/api/core/firmware/status
```

## Tailscale

Installed as a package on OPNsense. Provides remote access to the LAN without exposing any ports. No Cloudflare tunnel is used for LAN services.

## Roadmap

- [ ] Config export via API → encrypted commit to git (weekly cron) — see ROADMAP.md
- [ ] Firewall rules documented in `network/opnsense/rules.md`
