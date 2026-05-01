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

Gitea was migrated from CT 119 (decommissioned) to CT 123 in early 2026. Migration is complete. Historical migration commands are preserved in git history if needed for reference.
