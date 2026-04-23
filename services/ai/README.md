# AI VM (VM 134)

## Specs
- **VMID:** 134
- **Name:** ai
- **IP:** 192.168.x.170
- **OS:** Ubuntu 24.04 (cloud-init)
- **CPU:** 8 vCPU (x86-64-v2-AES)
- **RAM:** 32GB
- **Disk:** 128GB (vmpool)
- **GPU:** NVIDIA RTX A2000 12GB (PCI 0000:65:00, PCIe passthrough)
- **Machine:** q35, OVMF
- **Tags:** khris,gpu,ai

## Services
- Stable Diffusion (port 7860) — `stable.yourdomain.com`

## Access
- SSH: root@192.168.x.170 (claude-ops ed25519 key)
- Docker: 29.4.1 + Compose v5.1.3
- NVIDIA: Driver 570, Container Toolkit, CUDA 12.8

## Deploy
```
HOST=192.168.x.170
```

## Proxmox Config
```ini
bios: ovmf
boot: order=scsi0
ciuser: khris
cores: 8
cpu: x86-64-v2-AES
efidisk0: local-zfs:vm-134-disk-0,efitype=4m,size=1M
hostpci0: 0000:65:00,pcie=1
ide2: vmpool:vm-134-cloudinit,media=cdrom
ipconfig0: ip=192.168.x.170/24,gw=192.168.x.1
machine: q35
memory: 32768
name: ai
net0: virtio=BC:24:11:FC:BA:3C,bridge=vmbr0,firewall=0
onboot: 1
ostype: l26
scsi0: vmpool:vm-134-disk-0,iothread=1,size=128G
scsihw: virtio-scsi-pci
sshkeys: ssh-ed25519 ...root@openclaw
tags: khris,gpu,ai
```
