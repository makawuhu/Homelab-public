# Anri Installation Steps

## Prerequisites

- [ ] Proxmox access (khris@pve!ct103 token or root on Proxmox host)
- [ ] DNS access (OPNsense API credentials)
- [ ] NPM admin credentials (from SOPS)
- [ ] Discord bot token for Anri-Bot
- [ ] Telegram bot token for @yourhostnameanribot
- [ ] Brave Search API key
- [ ] Anthropic API key (for escalation)
- [ ] Ollama endpoint running (ollama.yourdomain.com)
- [ ] Honcho instance running (192.168.x.5:8050)

## Step 1: Create LXC

```bash
# On Proxmox host
pct create 129 local-zfs:vztmpl/debian-12-standard_12.2-1_amd64.tar.zst \
  --hostname anri \
  --cores 8 --memory 16384 --swap 512 \
  --net0 name=eth0,bridge=vmbr0,ip=192.168.x.165/24,gw=192.168.x.1 \
  --features nesting=1,keyctl=1 \
  --rootfs local-zfs:128 \
  --onboot 1
```

## Step 2: Start and Configure

```bash
pct start 129
pct enter 129
apt update && apt upgrade -y
# Install Node.js + OpenClaw
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt install -y nodejs
npm install -g openclaw
```

## Step 3: Configure OpenClaw

```bash
openclaw init
# Configure via openclaw.json:
# - Model: ollama/glm-5.1:cloud (primary)
# - Ollama base URL: http://ollama.yourdomain.com
# - Telegram channel config (bot token)
# - Discord channel config (bot token, allowlist)
# - Gateway bind: lan, auth token
# - Brave search plugin
# - Honcho memory plugin (workspace: anri)
```

## Step 4: Set Up Workspace Files

Copy SOUL.md, USER.md, TOOLS.md, IDENTITY.md, AGENTS.md, HEARTBEAT.md to `/root/.openclaw/workspace/`.

## Step 5: Create DNS Entry

```bash
# Add anri.yourdomain.com → 192.168.x.31 via OPNsense API
```

## Step 6: Create NPM Proxy Host

```bash
# Add anri.yourdomain.com → 192.168.x.165:18789
# cert_id: 2, HSTS, HTTP/2, websockets
```

## Step 7: Create Telegram Bot

1. Message @BotFather on Telegram
2. Create new bot: @yourhostnameanribot
3. Get bot token
4. Configure in openclaw.json

## Step 8: Create Discord Bot

1. Go to discord.com/developers
2. Create "Anri-Bot" application
3. Enable Message Content Intent
4. Get bot token
5. Configure in openclaw.json

## Step 9: Verify

- [ ] Anri responds to Telegram messages
- [ ] Anri responds to Discord messages
- [ ] SD generation works via stable.yourdomain.com
- [ ] Brave web search works
- [ ] Honcho memory plugin connected
- [ ] HTTPS endpoint works at https://anri.yourdomain.com

## Rollback

1. Stop OpenClaw gateway on CT 129
2. `pct stop 129 && pct destroy 129`
3. Remove DNS entry anri.yourdomain.com
4. Remove NPM proxy host (ID 91)
5. Delete Telegram bot (@yourhostnameanribot)
6. Delete Discord bot (Anri-Bot)