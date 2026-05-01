# Bazzite (VM 105) — DESTROYED 2026-04-16

**Status:** Destroyed — RTX 4070 SUPER and WD Black NVMe are now free on the PVE host, reserved for a dedicated GPU worker LXC.

## Historical specs

| Resource | Allocation |
|----------|-----------|
| vCPU | 8 |
| RAM | 16 GB |
| OS | Bazzite (Fedora-based immutable gaming OS) |
| GPU | NVIDIA RTX 4070 SUPER (`0000:17:00`) — full passthrough |
| Storage | WD Black SN850X 2TB NVMe (`0000:04:00`) — full passthrough |

## Hardware now available

| PCI | Device | Status |
|-----|--------|--------|
| `0000:17:00` | NVIDIA RTX 4070 SUPER | Free on PVE host |
| `0000:04:00` | WD Black SN850X 2TB NVMe | Free on PVE host |
