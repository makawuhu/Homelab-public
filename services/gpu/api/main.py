"""
GPU Compute API v2.1
GPU compute service with BullMQ job queue integration.

Swagger docs: /docs | ReDoc: /redoc
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict
from enum import Enum
import subprocess
import json
import time
import redis
import os

REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379")
QUEUE_NAME = "gpu-jobs"
r = redis.from_url(REDIS_URL, decode_responses=True)

class JobType(str, Enum):
    image_generation = "image_generation"
    ml_inference = "ml_inference"
    custom_docker = "custom_docker"
    benchmark = "benchmark"
    autoforge = "autoforge"

class JobSubmit(BaseModel):
    """Submit a GPU compute job."""
    job_type: JobType = Field(..., description="Type of GPU job")
    payload: dict = Field(..., description="Job parameters. See job type docs for required fields.")
    priority: int = Field(0, ge=0, le=10, description="Priority (0=normal, 10=highest)")
    timeout_seconds: int = Field(300, ge=10, le=3600, description="Max runtime before kill")
    callback_url: Optional[str] = Field(None, description="URL to POST results to")

class JobResponse(BaseModel):
    job_id: str
    job_type: str
    status: str
    priority: int
    created_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[dict] = None
    error: Optional[str] = None

app = FastAPI(
    title="GPU Compute API",
    version="2.1.0",
    description="""
## GPU Compute Service

Serverless-style GPU compute for the yourhostname homelab. RTX 4070 Super, 12GB VRAM, CUDA 13.0.

**Primary consumer:** [Studio](https://studio.yourdomain.com) — image generation UI that submits SD jobs and polls for results.

### Job Types

#### `custom_docker` / `autoforge` — Run any Docker container with GPU access
**Payload fields:**
| Field | Required | Description |
|-------|----------|-------------|
| `image` | ✅ | Docker image (e.g. `nvidia/cuda:13.0.0-base-ubuntu24.04`) |
| `command` | ❌ | Command string (executed via `bash -c`) |
| `entrypoint` | ❌ | Override container entrypoint |
| `env` | ❌ | Dict of environment variables (`{"KEY": "value"}`) |
| `volumes` | ❌ | Dict of volume mounts (`{"/host/path": "/container/path"}`) |
| `workdir` | ❌ | Working directory inside container |
| `shm_size` | ❌ | Shared memory size (default: `1g`, needed for PyTorch) |
| `network` | ❌ | Docker network (default: `host`) |

**Studio image generation example:**
```json
{
    "job_type": "custom_docker",
    "payload": {
        "image": "sd-job:local",
        "env": {
            "PROMPT": "a cyberpunk cityscape at sunset",
            "NEGATIVE_PROMPT": "blurry, low quality",
            "STEPS": "30",
            "WIDTH": "1024",
            "HEIGHT": "1024",
            "GUIDANCE_SCALE": "7.5",
            "MODEL_PATH": "/models/juggernaut-xl-v9.safetensors"
        },
        "volumes": {"/opt/models": "/models", "/opt/outputs": "/output"},
        "shm_size": "2g"
    },
    "timeout_seconds": 180
}
```

**AutoForge example:**
```json
{
    "job_type": "autoforge",
    "payload": {
        "image": "ghcr.io/yourhostname/autoforge-worker:latest",
        "command": "python -m autoforge run --config /workspace/job.json",
        "env": {"GITHUB_TOKEN": "ghp_...", "OUTPUT_DIR": "/workspace/output"},
        "volumes": {"/tmp/autoforge-workspace": "/workspace"},
        "shm_size": "4g"
    },
    "timeout_seconds": 600
}
```

#### `benchmark` — GPU stats snapshot
**Payload fields:**
| Field | Required | Description |
|-------|----------|-------------|
| `duration_seconds` | ❌ | Benchmark duration (default: 10) |

### Quick Start
1. `POST /jobs` — Submit a job
2. `GET /jobs/{job_id}` — Check status
3. `GET /models` — List available SD models
4. `GET /queue/stats` — Queue overview

### Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/jobs` | POST | Submit a GPU compute job |
| `/jobs` | GET | List jobs (filter by status) |
| `/jobs/{job_id}` | GET | Get job status and results |
| `/jobs/{job_id}` | DELETE | Cancel a queued job |
| `/models` | GET | List available model files |
| `/queue/stats` | GET | Queue statistics |
| `/health` | GET | GPU health + queue depth |
| `/gpu` | GET | Detailed GPU info |

### Studio Integration
[Studio](https://studio.yourdomain.com) uses this API to generate images:
1. `GET /models` — Populate model dropdown
2. `POST /jobs` — Submit an SD generation job (type: `custom_docker`, image: `sd-job:local`)
3. `GET /jobs/{job_id}` — Poll every 3s until `completed`
4. Result `stdout` contains the output filename → fetch from `https://gpu-outputs.yourdomain.com/{filename}`
""",
    contact={"name": "Khris", "url": "https://gpu.yourdomain.com"},
    license_info={"name": "MIT"},
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

def get_gpu_stats() -> dict:
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,driver_version,memory.total,memory.used,memory.free,utilization.gpu,temperature.gpu,power.draw",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            parts = [p.strip() for p in result.stdout.strip().split(",")]
            return {
                "name": parts[0], "driver": parts[1],
                "memory_total_mb": float(parts[2]), "memory_used_mb": float(parts[3]),
                "memory_free_mb": float(parts[4]), "gpu_util_pct": float(parts[5]),
                "temperature_c": float(parts[6]),
                "power_draw_w": float(parts[7].split(".")[0]) if "." in parts[7] else float(parts[7])
            }
    except Exception:
        pass
    return None

@app.get("/", tags=["Service"])
async def root():
    """Service info."""
    redis_ok = False
    try: redis_ok = r.ping()
    except Exception: pass
    return {"service": "gpu", "status": "running", "version": "2.1.0", "docs_url": "/docs", "redis_connected": redis_ok}

@app.get("/health", tags=["Monitoring"])
async def health():
    """GPU health + queue depth."""
    gpu = get_gpu_stats()
    try:
        qd = r.zcard(f"bull:{QUEUE_NAME}:wait") or 0
        wa = r.scard(f"bull:{QUEUE_NAME}:active") or 0
        ro = True
    except Exception:
        qd, wa, ro = 0, 0, False
    return {"status": "healthy" if gpu else "degraded", "gpu": gpu, "queue_depth": qd, "workers_active": wa, "redis_connected": ro}

@app.get("/gpu", tags=["Monitoring"])
async def gpu_info():
    """Detailed GPU info."""
    gpu = get_gpu_stats()
    if not gpu: raise HTTPException(status_code=503, detail="GPU not available")
    return gpu

@app.post("/jobs", response_model=JobResponse, status_code=201, tags=["Jobs"])
async def submit_job(job: JobSubmit):
    """Submit a GPU compute job. See job type docs above for payload format."""
    job_id = f"gpu-job-{int(time.time() * 1000)}"
    now = time.time()
    job_data = {
        "id": job_id, "type": job.job_type.value,
        "payload": json.dumps(job.payload), "priority": str(job.priority),
        "status": "queued", "created_at": str(now),
        "started_at": "", "completed_at": "", "result": "", "error": "",
        "timeout": str(job.timeout_seconds),
        "callback_url": job.callback_url or "",
        "attempts": "0", "max_attempts": "3",
    }
    r.hset(f"bull:{QUEUE_NAME}:{job_id}", mapping=job_data)
    r.zadd(f"bull:{QUEUE_NAME}:wait", {job_id: now - (job.priority * 1000)})
    r.sadd(f"bull:{QUEUE_NAME}:jobs", job_id)
    return {"job_id": job_id, "job_type": job.job_type.value, "status": "queued",
            "priority": job.priority, "created_at": now,
            "started_at": None, "completed_at": None, "result": None, "error": None}

@app.get("/jobs", tags=["Jobs"])
async def list_jobs(status: Optional[str] = Query(None), limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    """List jobs. Optional filter by status."""
    try:
        job_ids = list(r.smembers(f"bull:{QUEUE_NAME}:jobs") or set())
        jobs = []
        for jid in job_ids[offset:offset+limit]:
            data = r.hgetall(f"bull:{QUEUE_NAME}:{jid}")
            if data:
                js = data.get("status", "unknown")
                if status and js != status: continue
                jobs.append({
                    "job_id": jid, "job_type": data.get("type", ""), "status": js,
                    "priority": int(data.get("priority", 0)),
                    "created_at": float(data.get("created_at", 0)),
                    "started_at": float(data["started_at"]) if data.get("started_at") else None,
                    "completed_at": float(data["completed_at"]) if data.get("completed_at") else None,
                    "result": json.loads(data["result"]) if data.get("result") else None,
                    "error": data.get("error") or None
                })
        jobs.sort(key=lambda x: x["created_at"], reverse=True)
        return {"total": len(jobs), "offset": offset, "limit": limit, "jobs": jobs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/jobs/{job_id}", response_model=JobResponse, tags=["Jobs"])
async def get_job(job_id: str):
    """Get job status and results."""
    data = r.hgetall(f"bull:{QUEUE_NAME}:{job_id}")
    if not data: raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return {"job_id": job_id, "job_type": data.get("type", ""), "status": data.get("status", "unknown"),
            "priority": int(data.get("priority", 0)),
            "created_at": float(data.get("created_at", 0)),
            "started_at": float(data["started_at"]) if data.get("started_at") else None,
            "completed_at": float(data["completed_at"]) if data.get("completed_at") else None,
            "result": json.loads(data["result"]) if data.get("result") else None,
            "error": data.get("error") or None}

@app.delete("/jobs/{job_id}", tags=["Jobs"])
async def cancel_job(job_id: str):
    """Cancel a queued job."""
    data = r.hgetall(f"bull:{QUEUE_NAME}:{job_id}")
    if not data: raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    if data.get("status") == "running": raise HTTPException(status_code=409, detail="Cannot cancel running job")
    if data.get("status") in ("completed", "failed", "cancelled"): raise HTTPException(status_code=409, detail=f"Job already {data['status']}")
    r.zrem(f"bull:{QUEUE_NAME}:wait", job_id)
    r.hset(f"bull:{QUEUE_NAME}:{job_id}", "status", "cancelled")
    return {"job_id": job_id, "status": "cancelled"}

@app.get("/models", tags=["Models"])
async def list_models():
    """List available model files in /opt/models."""
    import glob
    models = []
    for path in sorted(glob.glob("/opt/models/*.safetensors") + glob.glob("/opt/models/*.ckpt")):
        name = os.path.basename(path)
        size_gb = round(os.path.getsize(path) / (1024**3), 1)
        is_xl = "xl" in name.lower()
        container_path = "/models/" + name
        models.append({"name": name, "path": path, "container_path": container_path, "size_gb": size_gb, "is_xl": is_xl})
    return {"models": models}

@app.get("/queue/stats", tags=["Queue"])
async def queue_stats():
    """Queue statistics."""
    try:
        return {
            "queue_name": QUEUE_NAME,
            "total_jobs": r.scard(f"bull:{QUEUE_NAME}:jobs") or 0,
            "waiting": r.zcard(f"bull:{QUEUE_NAME}:wait") or 0,
            "active": r.scard(f"bull:{QUEUE_NAME}:active") or 0,
            "completed": r.scard(f"bull:{QUEUE_NAME}:completed") or 0,
            "failed": r.scard(f"bull:{QUEUE_NAME}:failed") or 0,
            "redis_connected": r.ping()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))