# Ash Installation Steps (Hermes Agent + Pokemon Blue)

## Prerequisites

- [ ] Proxmox root SSH access
- [ ] Telegram bot token (store in ~/.hermes/.env on CT, never in git)
- [ ] Pokemon Blue ROM at /root/roms/pokemon-blue.gb

## Step 1: Create LXC

```bash
# On Proxmox host (192.168.x.4)
pct create 136 local:vztmpl/debian-12-standard_12.12-1_amd64.tar.zst \
  --hostname ash \
  --cores 4 --memory 8192 --swap 512 \
  --net0 name=eth0,bridge=vmbr0,ip=192.168.x.172/24,gw=192.168.x.1 \
  --nameserver 192.168.x.1 \
  --features nesting=1,keyctl=1 \
  --rootfs vmpool:32 \
  --onboot 1

pct start 136
```

## Step 2: Install Base Dependencies

```bash
pct exec 136 -- bash -c "apt update && apt upgrade -y && apt install -y \
  curl git build-essential python3-dev libffi-dev ripgrep openssh-server \
  python3 python3-venv python3-pip libsdl2-dev"
```

## Step 3: Install Hermes Agent

```bash
pct exec 136 -- bash -c "curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash"
```

## Step 4: Configure Hermes

```bash
pct exec 136 -- bash -c "mkdir -p /root/.hermes/logs"

pct exec 136 -- bash -c "cat > /root/.hermes/config.yaml << 'EOF'
model:
  provider: \"openai-codex\"
  base_url: \"https://chatgpt.com/backend-api/codex\"
  default: \"gpt-5.5\"
  api_key: \"unused\"

terminal:
  backend: \"local\"
  cwd: \"/root\"
EOF"

# Write .env with Telegram token — do not commit this token to git
pct exec 136 -- bash -c "cat > /root/.hermes/.env << 'EOF'
TELEGRAM_BOT_TOKEN=<token-goes-here>
GATEWAY_ALLOW_ALL_USERS=true
EOF"
```

## Step 5: Install pokemon-agent

```bash
pct exec 136 -- bash -c "
  git clone https://github.com/NousResearch/pokemon-agent /opt/pokemon-agent-src
  python3 -m venv /opt/pokemon-agent
  /opt/pokemon-agent/bin/pip install -e '/opt/pokemon-agent-src[pyboy]'
"
```

## Step 6: Copy ROM

```bash
# From claude-ops CT or Proxmox host
scp /root/'Pokemon - Blue Version (USA, Europe) (SGB Enhanced).gb' root@192.168.x.4:/tmp/pokemon-blue.gb
ssh root@192.168.x.4 "pct exec 136 -- mkdir -p /root/roms && pct push 136 /tmp/pokemon-blue.gb /root/roms/pokemon-blue.gb"
```

## Step 7: Systemd — pokemon-game.service

```bash
pct exec 136 -- bash -c "cat > /etc/systemd/system/pokemon-game.service << 'EOF'
[Unit]
Description=Pokemon Agent Game Server
After=network.target

[Service]
Type=simple
User=root
ExecStart=/opt/pokemon-agent/bin/pokemon-agent serve --rom /root/roms/pokemon-blue.gb --port 9876
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable pokemon-game
systemctl start pokemon-game"
```

## Step 8: Systemd — hermes.service

```bash
pct exec 136 -- bash -c "cat > /etc/systemd/system/hermes.service << 'EOF'
[Unit]
Description=Hermes Agent Gateway (Ash)
After=network.target pokemon-game.service

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
systemctl start hermes"
```

## Step 9: Verify

```bash
# Game server health
pct exec 136 -- curl -s http://localhost:9876/health

# Hermes connected
pct exec 136 -- journalctl -u hermes -n 30
pct exec 136 -- tail -20 /root/.hermes/logs/agent.log
```

## Rollback

```bash
systemctl stop hermes pokemon-game
systemctl disable hermes pokemon-game
pct stop 136 && pct destroy 136
```
