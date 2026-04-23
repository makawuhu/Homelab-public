# Khris Installation Steps

## Prerequisites

- [ ] Proxmox access (khris@pve!ct103 token or root on Proxmox host)
- [ ] OPNsense DNS access
- [ ] NPM admin credentials (from SOPS)
- [ ] Discord bot token for Khris-Bot
- [ ] Brave Search API key
- [ ] Ollama endpoint running (ollama.yourdomain.com)

## Step 1: Create LXC

```bash
# On Proxmox host
pct create 103 local-zfs:vztmpl/debian-12-standard_12.2-1_amd64.tar.zst \
  --hostname khris \
  --cores 4 --memory 16384 --swap 512 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --features nesting=1,keyctl=1 \
  --rootfs local-zfs:128
```

## Step 2: Start and Configure

```bash
pct start 103
pct enter 103
# Install Docker, OpenClaw, Git, SOPS, Node.js
apt update && apt upgrade -y
curl -fsSL https://get.docker.com | sh
npm install -g openclaw
apt install -y git age sops
```

## Step 3: Configure OpenClaw

```bash
openclaw init
# Configure via openclaw.json:
# - Model: ollama/glm-5.1:cloud (primary)
# - Ollama base URL: http://ollama.yourdomain.com
# - Discord channel config
# - Gateway bind: lan
# - Brave search plugin
```

## Step 4: Set Up Workspace Files

Copy SOUL.md, USER.md, TOOLS.md, IDENTITY.md, AGENTS.md, HEARTBEAT.md to `/root/.openclaw/workspace/`.

## Step 5: Set Up GitOps Pipeline

```bash
# Clone homelab repo
git clone http://192.168.x.48:3010/your-gitea-user/homelab.git /opt/homelab
# Install SOPS age key
mkdir -p /root/.age
cp age.key /root/.age/key.txt
```

## Step 6: Start Services

```bash
# Start OpenClaw gateway (runs as bare process, no systemd unit)
openclaw gateway start

# Start Docker services
# webhook-prod (GitOps deploy)
cd /opt/homelab/services/webhook && docker compose up -d

# Authentik (SSO)
cd /opt/homelab/services/authentik && docker compose up -d
```

## Step 7: Create Discord Bot

1. Go to discord.com/developers
2. Create "Khris-Bot" application
3. Enable Message Content Intent
4. Get bot token
5. Configure in openclaw.json

## Step 8: Verify

- [ ] Khris responds to Discord messages
- [ ] Khris can execute commands on infrastructure
- [ ] GitOps webhook fires on push to main
- [ ] SOPS can decrypt secrets
- [ ] Health check cron runs at 8am PST

## Rollback

1. Stop OpenClaw and Docker services on CT 103
2. `pct stop 103 && pct destroy 103` (removes all data including webhook-prod)
3. Remove Discord bot
4. **Warning:** This takes out the entire GitOps deploy pipeline — restore webhook-prod elsewhere first