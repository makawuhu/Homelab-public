# Nginx Proxy Manager

**Host:** CT 104 (nginxproxymanager) · `192.168.x.31`
**Stack:** openresty 1.27.1.2 + Node.js (NPM) + certbot — native services (NOT Docker)
**Installed via:** [Proxmox community helper scripts](https://helper-scripts.com)

## Access

| URL | Description |
|-----|-------------|
| `http://nginx.yourdomain.com` | Admin UI (external) |
| `http://192.168.x.31:81` | Admin UI (direct LAN) |
| `:80` / `:443` | Proxied traffic |

## Notes

- `onboot: 1` — starts automatically with Proxmox
- SSL certificates managed by certbot via NPM UI
- `lxc.cgroup2.devices.allow: c 10:200 rwm` — TUN device allowed for VPN-proxied hosts
