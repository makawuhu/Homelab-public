# Tao Installation Steps

## Prerequisites

- [ ] Proxmox access (khris@pve!ct103 token or root on Proxmox host)
- [ ] DNS access (OPNsense API credentials)
- [ ] NPM admin credentials (from SOPS)
- [ ] Discord bot token for Tao-Bot
- [ ] Brave Search API key
- [ ] Ollama endpoint running (ollama.yourdomain.com)
- [ ] Gitea access for homelab repo (read-only token)

## Step 1: Create LXC

```bash
# On Proxmox host
pct create 133 vmpool:vztmpl/debian-12-standard_12.2-1_amd64.tar.zst \
  --hostname tao \
  --cores 2 --memory 4096 --swap 512 \
  --net0 name=eth0,bridge=vmbr0,ip=dhcp \
  --features nesting=1,keyctl=1 \
  --rootfs vmpool:32 \
  --onboot 1
```

## Step 2: Start and Configure

```bash
pct start 133
pct enter 133
apt update && apt upgrade -y
# Install Node.js + OpenClaw
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt install -y nodejs git
npm install -g openclaw
```

## Step 3: Clone Homelab Repo

```bash
git clone http://192.168.x.48:3010/your-gitea-user/homelab.git /root/homelab
# This is Tao's primary knowledge source — read-only access
```

## Step 4: Configure OpenClaw

```bash
openclaw init
# Configure via openclaw.json:
# - Model: ollama/glm-5.1:cloud (primary), minimax-m2.7:cloud (fallback)
# - Ollama base URL: http://ollama.yourdomain.com
# - Discord channel config (bot token, allowlist, allowBots: true)
# - Gateway bind: lan, auth: token mode
# - Brave search plugin
# - No Telegram, no SOPS secrets, no Honcho
```

## Step 5: Set Up Workspace Files

Copy SOUL.md, USER.md, TOOLS.md, IDENTITY.md, AGENTS.md, HEARTBEAT.md to `/root/.openclaw/workspace/`.

## Step 6: Create DNS Entry

```bash
# Add tao.yourdomain.com → 192.168.x.31 via OPNsense API
```

## Step 7: Create NPM Proxy Host

```bash
# Add tao.yourdomain.com → 192.168.x.169:18789
# cert_id: 2, HSTS, HTTP/2, websockets
```

## Step 8: Create Discord Bot

1. Go to discord.com/developers
2. Create "Tao-Bot" application
3. Enable Message Content Intent
4. Get bot token
5. Configure in openclaw.json

## Step 9: Verify

- [ ] Tao responds to Discord messages
- [ ] Tao can read and answer questions about the homelab repo
- [ ] Other agents can query Tao via Discord or gateway API
- [ ] HTTPS endpoint works at https://tao.yourdomain.com

## Rollback

1. Stop OpenClaw gateway on CT 133
2. `pct stop 133 && pct destroy 133`
3. Remove DNS entry tao.yourdomain.com
4. Remove NPM proxy host (ID 90)
5. Delete Discord bot (Tao-Bot)