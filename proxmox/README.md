# Proxmox Host

**Hostname:** pve · `192.168.x.4`
**Kernel:** 6.17.2-2-pve
**Web UI:** `https://192.168.x.4:8006`

## GPUs

| PCI | Device | Current Assignment |
|-----|--------|--------------------|
| 0000:17:00 | RTX 4070 SUPER | VM 131 (gpu) |
| 0000:65:00 | RTX A2000 12GB | VM 134 (ai) |

## NVMe

| PCI | Device | Status |
|-----|--------|--------|
| 0000:04:00 | WD Black SN850X 2TB | Free on PVE host (VM 105 Bazzite destroyed 2026-04-16) |

## ZFS

- **rpool** (472G) — OS, LXC rootfs for CT102/104/112, VM disks for VM101
- **vmpool** (1.73T) — bulk storage, VM disk for VM108

## Hardware

**Model:** Dell Precision 7820 Workstation — purchased for $336 shipped as a purpose-built homelab server.

| Component | Detail |
|-----------|--------|
| CPU | Intel Xeon Gold 6248 @ 2.50 GHz (40 threads, 1 socket) |
| RAM | 187 GB DDR4 ECC — supports up to 384 GB |
| Storage | 512 GB SK Hynix (OS) · 1.92 TB Intel DC SSD (VMs) · 4 TB WD Red (media) · 2 TB WD Black SN850X NVMe (games/passthrough) · 128 GB Fujitsu (unused) |
| GPU 0 | NVIDIA RTX 4070 SUPER — `0000:17:00` |
| GPU 1 | NVIDIA RTX A2000 12GB — `0000:65:00` |

Server-grade choice for ECC RAM stability, dual-socket expandability, PCIe lane count, and price-to-performance at the used enterprise market.

## Hypervisor

Proxmox VE was chosen after testing Proxmox, Hyper-V, KVM (Ubuntu), and Unraid on laptops before committing to dedicated hardware. Key reasons:
- Free community edition, Debian-based (familiar CLI)
- First-class LXC + VM support with web UI
- Built-in backup, snapshot, and ZFS tooling

Initial testing was done on a Dell Precision 5540 laptop (later sold to fund this hardware).

## Initial Setup

- Proxmox installed via USB to SK Hynix 512 GB SSD
- Bridge `vmbr0` on `nic4` — `192.168.x.4/24`, gateway `192.168.x.1`
- ZFS chosen over LVM for snapshot and data integrity features
- `rpool` on 512 GB SSD (OS + small VM disks), `vmpool` on 1.92 TB Intel SSD (bulk VM storage)
- VM backups stored on 4 TB WD Red via `usb-backup` storage target

## Related Repos

- [Ollama-Model-Manager](https://github.com/yourhostname/Ollama-Model-Manager) — web UI for managing local Ollama models
- [proxmox-vm-controller](https://github.com/yourhostname/proxmox-vm-controller) — browser-based VM start/stop

## Undocumented Services (on portainer VM)

These run on VM 101 (`192.168.x.5`) but don't have external proxy entries yet:

- **Samba/NAS** — SMB file sharing (:445, :139)
- **CUPS** — Print server (:631)
- **ARM Ripper** — DVD ripping automation (see VM 108 `dvdripper`)

## Useful Commands

```bash
# List all VMs/LXCs
pvesh get /nodes/pve/lxc
pvesh get /nodes/pve/qemu

# Start/stop a container
pct start 103
pct stop 103

# Execute in LXC
pct exec 103 -- bash

# ZFS status
zpool status
zfs list
```
