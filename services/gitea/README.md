# Gitea — CT 123 (`192.168.x.48`)

Gitea git server + Postgres, running on a dedicated LXC (CT 123).

- UI: https://gitea.yourdomain.com
- Internal: `http://192.168.x.48:3010`
- SSH: `192.168.x.48:2222`

---

## Provisioning CT 123 (first time)

```bash
# On Proxmox host
pct create 123 local:vztmpl/ubuntu-24.04-standard_24.04-2_amd64.tar.zst \
  --hostname gitea \
  --cores 2 \
  --memory 4096 \
  --swap 512 \
  --rootfs local-zfs:20 \
  --net0 name=eth0,bridge=vmbr0,ip=192.168.x.48/24,gw=192.168.x.1 \
  --features nesting=1,fuse=1 \
  --unprivileged 1 \
  --start 1

# Authorize claude-ops SSH key
pct exec 123 -- bash -c "mkdir -p /root/.ssh && echo 'SSH_PUBLIC_KEY' >> /root/.ssh/authorized_keys && chmod 600 /root/.ssh/authorized_keys"
```

### Install Docker CE + fuse-overlayfs (required for ZFS-backed unprivileged LXC)

```bash
ssh root@192.168.x.48 bash << 'EOF'
apt-get update -qq
apt-get install -y -qq curl ca-certificates gnupg lsb-release fuse-overlayfs
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
  > /etc/apt/sources.list.d/docker.list
apt-get update -qq
apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
mkdir -p /etc/docker
echo '{"storage-driver": "fuse-overlayfs"}' > /etc/docker/daemon.json
systemctl restart docker
docker info | grep "Storage Driver"
EOF
```

---

## Migration from CT 119

### 1. Stop Gitea on CT 119 (leave DB running)

```bash
ssh root@192.168.x.45 'docker stop gitea'
```

### 2. Dump Gitea data

```bash
ssh root@192.168.x.45 'docker exec -u git gitea gitea dump -c /data/gitea/conf/app.ini --type zip -f /tmp/gitea-dump.zip'
scp root@192.168.x.45:/tmp/gitea-dump.zip /tmp/gitea-dump.zip
scp /tmp/gitea-dump.zip root@192.168.x.48:/tmp/gitea-dump.zip
```

### 3. Start DB on CT 123, restore dump

```bash
ssh root@192.168.x.48 'cd /opt/gitea && docker compose up -d gitea-db'

ssh root@192.168.x.48 bash << 'EOF'
cd /tmp && unzip -q gitea-dump.zip -d gitea-restore && cd gitea-restore
docker exec -i gitea-db psql -U gitea gitea < gitea-db.sql
GITEA_DATA=$(docker volume inspect gitea-data --format '{{.Mountpoint}}')
[ -d repositories ] && cp -a repositories/ "${GITEA_DATA}/repositories/"
for dir in attachments lfs avatars; do
  [ -d "$dir" ] && cp -a "$dir" "${GITEA_DATA}/gitea/$dir"
done
mkdir -p "${GITEA_DATA}/gitea/conf"
cp gitea-app.ini "${GITEA_DATA}/gitea/conf/app.ini"
chown -R 1000:1000 "${GITEA_DATA}"
EOF
```

### 4. Start Gitea on CT 123 and verify

```bash
ssh root@192.168.x.48 'cd /opt/gitea && docker compose up -d gitea'
curl -s http://192.168.x.48:3010/api/v1/version
```

### 5. Update NPM proxy

Add `gitea.yourdomain.com` → `192.168.x.48:3010` via NPM API.
