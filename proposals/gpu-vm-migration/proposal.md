# Proposal: Dedicated AI VM Migration (RTX A2000)

## 1. Overview
**Goal:** Move the RTX A2000 GPU and its associated services from VM 101 to a dedicated AI VM to isolate GPU workloads and improve stability.

**Risk Level:** High (Hardware passthrough and production service migration)

## 2. Specification
### New VM (AI-GPU)
- **OS:** Ubuntu 24.04 (Cloud Image)
- **CPU:** 8 vCPUs
- **RAM:** 32GB ECC
- **Disk:** 100GB (vmpool)
- **Network:** Bridge (standard homelab subnet)
- **Hardware:** PCI Passthrough of RTX A2000

### Services to Migrate
- `stable-diffusion` (sd-auto:local)
- Any other identified GPU-bound containers on VM 101

## 3. Execution Plan

### Phase 1: Provisioning
1. Create new VM (AI-GPU) via Proxmox API.
2. Configure Cloud-init for root access and basic networking.
3. Attach the RTX A2000 PCI device from VM 101 $\rightarrow$ AI-GPU.

### Phase 2: Driver & Environment Setup
1. Install NVIDIA drivers (version matching the host/current stable).
2. Install NVIDIA Container Toolkit.
3. Verify GPU access with `nvidia-smi`.

### Phase 3: Service Migration
1. Stop `stable-diffusion` on VM 101.
2. Migrate the compose file and volumes to the new VM.
3. Deploy service on the new VM.
4. Update NPM proxy host to point to the new VM IP.

### Phase 4: Verification
1. Confirm `stable-diffusion` is reachable via `stable.yourdomain.com`.
2. Verify GPU utilization during image generation.
3. Clean up stale configs on VM 101.

## 4. Rollback Plan
- **Hardware:** Re-attach A2000 to VM 101.
- **Software:** Restart `stable-diffusion` on VM 101.
- **DNS/Proxy:** Revert NPM proxy host back to VM 101 IP.

## 5. Verification Criteria
- [ ] New VM is pingable and SSH-accessible.
- [ ] `nvidia-smi` reports the RTX A2000 correctly on the new VM.
- [ ] Stable Diffusion WebUI loads and generates images.
- [ ] External access via `stable.yourdomain.com` is restored.
