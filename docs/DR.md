# Disaster Recovery — Secrets & GitOps State

## Overview

All secrets are encrypted with SOPS + age and stored in the `secrets/` and `services/*/`
directories of this repo. In a DR scenario, the git repo + the age private key are
sufficient to fully reconstruct the homelab.

---

## Age Key

The age private key on the deploy host is the master secret. Without it, all `.sops`
files are unreadable.

**Location on deploy host:** `/root/.age/key.txt`

**Public key:** stored in `.sops.yaml` — replace with your own when forking.

### Backing up the key

```bash
cat /root/.age/key.txt
```

The file looks like:
```
# created: <timestamp>
# public key: age1...
AGE-SECRET-KEY-1...
```

Store the `AGE-SECRET-KEY-1...` line in a password manager or offline location.

---

## Recovery Procedure

### 1. Provision the deploy host

```bash
apt install -y age git docker.io
curl -L https://github.com/getsops/sops/releases/download/v3.12.2/sops-v3.12.2.linux.amd64 \
  -o /usr/local/bin/sops && chmod +x /usr/local/bin/sops
```

### 2. Restore the age key

```bash
mkdir -p /root/.age && chmod 700 /root/.age
cat > /root/.age/key.txt <<'EOKEY'
# created: <timestamp>
# public key: age1<YOUR_PUBLIC_KEY>
AGE-SECRET-KEY-1<YOUR_SECRET_KEY>
EOKEY
chmod 600 /root/.age/key.txt
```

### 3. Clone the repo

```bash
git clone http://your-gitea-user:<GITEA_TOKEN>@192.168.x.x:3010/your-gitea-user/homelab.git /root/homelab
```

### 4. Reconstruct /root/.secrets/

```bash
cd /root/homelab
mkdir -p /root/.secrets

for f in opnsense npm portainer uptime-kuma gmail gitea github renovate; do
  SOPS_AGE_KEY_FILE=/root/.age/key.txt sops --decrypt \
    --input-type dotenv --output-type dotenv \
    secrets/$f.sops > /root/.secrets/$f
done

SOPS_AGE_KEY_FILE=/root/.age/key.txt sops --decrypt \
  --input-type dotenv --output-type dotenv \
  secrets/wazuh.sops > /root/.secrets/wazuh.env

chmod 600 /root/.secrets/*
```

### 5. Reconstruct service .env files

```bash
cd /root/homelab
for svc_sops in services/*/.env.sops; do
  svc=$(dirname "$svc_sops" | cut -d/ -f2)
  deploy_file="services/$svc/.deploy"
  [ -f "$deploy_file" ] || continue
  HOST=$(grep '^HOST=' "$deploy_file" | cut -d= -f2 | tr -d '[:space:]')
  SOPS_AGE_KEY_FILE=/root/.age/key.txt sops --decrypt \
    --input-type dotenv --output-type dotenv "$svc_sops" \
    > "services/$svc/.env"
  scp "services/$svc/.env" "root@$HOST:/opt/homelab/services/$svc/.env"
  rm -f "services/$svc/.env"
  echo "Restored $svc → $HOST"
done
```

### 6. Redeploy services

The webhook deploy pipeline runs on CT 103 (192.168.x.163). Push to Gitea main
branch triggers webhook hooks that auto-deploy changed services.

For manual deploys:

```bash
bash /opt/homelab/services/webhook/scripts/deploy.sh
```

---

## What Lives Where

| Secret | Encrypted location | Live location |
|---|---|---|
| OPNsense API key | `secrets/opnsense.sops` | `/root/.secrets/opnsense` |
| NPM credentials | `secrets/npm.sops` | `/root/.secrets/npm` |
| Portainer API | `secrets/portainer.sops` | `/root/.secrets/portainer` |
| Uptime Kuma | `secrets/uptime-kuma.sops` | `/root/.secrets/uptime-kuma` |
| Gmail SMTP | `secrets/gmail.sops` | `/root/.secrets/gmail` |
| Gitea token | `secrets/gitea.sops` | `/root/.secrets/gitea` |
| GitHub PAT | `secrets/github.sops` | `/root/.secrets/github` |
| Renovate token | `secrets/renovate.sops` | `/root/.secrets/renovate` |
| Wazuh API | `secrets/wazuh.sops` | `/root/.secrets/wazuh.env` |
| WUD Gmail | `services/wud/.env.sops` | `/opt/homelab/services/wud/.env` on Docker host |
| Homepage API keys | `services/homepage/.env.sops` | `/opt/homelab/services/homepage/.env` on Docker host |
