# Max — OpenCode Agent (CT 135)

## Spec
- **CT ID:** 135
- **Hostname:** max
- **IP:** 192.168.x.171
- **OS:** Ubuntu 24.04
- **Cores:** 4 | **RAM:** 16GB | **Disk:** 128GB (vmpool)
- **Storage:** vmpool (production)
- **Purpose:** OpenCode AI coding agent
- **SSH:** khris key deployed, root login enabled

## Network
- **Gateway:** 192.168.x.1
- **DNS:** max.yourdomain.com → 192.168.x.31 (NPM) — *pending*
- **NPM Proxy:** *pending*

## Deployment
- Created: 2026-04-23
- Docker 29.4.1 + Compose v5.1.3
- Timezone: America/Los_Angeles

## Gate
- Gate 1: Plan & Classify ✅
- Gate 2: PR ✅ (this doc)
- Gate 3: Execute ✅ (CT created and running)