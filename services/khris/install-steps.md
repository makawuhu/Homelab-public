# Khris Installation Steps (Hermes Agent)

## Prerequisites

- [ ] Proxmox root SSH access
- [ ] CT 125 (Ollama) running with glm-5.1:cloud pulled
- [ ] Telegram bot token

## Step 1: Create LXC

```bash
# On Proxmox host
pct create 103 local:vztmpl/debian-12-standard_12.12-1_amd64.tar.zst \
  --hostname khris \
  --cores 8 --memory 16384 --swap 512 \
  --net0 name=eth0,bridge=vmbr0,ip=192.168.x.163/24,gw=192.168.x.1 \
  --nameserver 192.168.x.1 \
  --features nesting=1,keyctl=1 \
  --rootfs local-zfs:128 \
  --onboot 1

pct start 103
```

## Step 2: Install Base Dependencies

```bash
pct exec 103 -- bash -c "apt update && apt upgrade -y && apt install -y curl git build-essential python3-dev libffi-dev ripgrep openssh-server"
```

## Step 3: Install Hermes Agent

```bash
pct exec 103 -- bash -c "curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash"
# Setup wizard will fail (no TTY) — that's expected; configure manually in Step 4
```

## Step 4: Configure Hermes

Write `~/.hermes/config.yaml`:
```yaml
model:
  provider: "ollama"
  base_url: "http://192.168.x.51:11434/v1"
  default: "glm-5.1:cloud"
  api_key: "ollama"

terminal:
  backend: "local"
  cwd: "/root"
```

Write `~/.hermes/.env`:
```
TELEGRAM_BOT_TOKEN=<token>
GATEWAY_ALLOW_ALL_USERS=true
```

## Step 5: Set Up Systemd Service

```bash
cat > /etc/systemd/system/hermes.service << 'EOF'
[Unit]
Description=Hermes Agent Gateway
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root
ExecStart=/root/.local/bin/hermes gateway run
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable hermes
systemctl start hermes
```

## Step 6: Pull Model on CT 125

```bash
ssh root@192.168.x.4 'pct exec 125 -- bash -c "cd /opt/homelab/services/ollama && docker compose up -d && docker exec ollama ollama pull glm-5.1:cloud"'
```

## Step 7: Verify

```bash
# Check service
systemctl status hermes

# Check logs
tail -f ~/.hermes/logs/agent.log

# Confirm Telegram connected
grep "Connected to Telegram" ~/.hermes/logs/agent.log
```

## Rollback

1. `systemctl stop hermes && systemctl disable hermes`
2. `pct stop 103 && pct destroy 103`
