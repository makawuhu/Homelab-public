import asyncio
import csv
import io
import json
import math
import os
import re
import stat
import shutil
import time
from pathlib import Path
from typing import Optional

import httpx
import paramiko
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import make_3mf

HUEFORGE_BASE     = os.environ.get("HUEFORGE_BASE", "/data/hueforge")
RUNPOD_API_KEY    = os.environ.get("RUNPOD_API_KEY", "")
RUNPOD_POD_ID     = os.environ.get("RUNPOD_POD_ID", "")
RUNPOD_GQL        = "https://api.runpod.io/graphql"
RUNPOD_SSH_KEY    = os.environ.get("RUNPOD_SSH_KEY_PATH", "/run/secrets/runpod-ssh-key")
LOCAL_GPU_HOST    = os.environ.get("LOCAL_GPU_HOST", "192.168.x.5")
SD_API_URL        = os.environ.get("SD_API_URL", "http://192.168.x.5:7860")

_TQDM_LINE = re.compile(r'^\s*\d+%\|')
_ITER_LINE = re.compile(r'(Iteration \d+[^:]+)')

TRUCK_REF = os.environ.get(
    "TRUCK_REF_PATH",
    f"{HUEFORGE_BASE}/Truckee river test/truckee-river_Front_200x133.3mf"
)
LIBRARY_PATH = os.path.join(HUEFORGE_BASE, "my-filaments.json")

generate_lock  = asyncio.Lock()
autoforge_lock = asyncio.Lock()

app = FastAPI()


# ── Helpers ──────────────────────────────────────────────────────────────────

def _resolve_stl(project_dir: str) -> Optional[str]:
    for candidate in ["pass2/final_model.stl", "final_model.stl"]:
        p = os.path.join(project_dir, candidate)
        if os.path.exists(p):
            return p
    return None


def _parse_hfp(project_dir: str) -> Optional[dict]:
    hfp_path = os.path.join(project_dir, "project_file.hfp")
    if not os.path.exists(hfp_path):
        return None
    with open(hfp_path) as f:
        data = json.load(f)
    seen_keys = set()
    filaments = []
    for fil in data.get("filament_set", []):
        key = (fil.get("Brand", "").lower(), fil.get("Name", "").lower())
        if key in seen_keys:
            continue
        seen_keys.add(key)
        filaments.append({
            "brand": fil.get("Brand", ""),
            "name":  fil.get("Name", ""),
            "type":  fil.get("Type", "PLA"),
            "color": fil.get("Color", "#000000"),
            "td":    fil.get("Transmissivity", fil.get("TD", 0)),
        })
    return {
        "layer_height":      data.get("layer_height", 0.08),
        "base_layer_height": data.get("base_layer_height", 0.56),
        "filaments":         filaments,
    }


def _parse_swap_instructions(project_dir: str) -> Optional[dict]:
    path = os.path.join(project_dir, "swap_instructions.txt")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        text = f.read()

    bg_match = re.search(r'using background filament (.+)', text)
    background = bg_match.group(1).strip() if bg_match else ""

    swaps = []
    for m in re.finditer(r'At layer #(\d+) \(([\d.]+)mm\) swap to (.+)', text):
        swaps.append({
            "layer":         int(m.group(1)),
            "top_z":         float(m.group(2)),
            "filament_name": m.group(3).strip().rstrip('.'),
        })
    return {"background_filament": background.rstrip('.'), "swaps": swaps}


def _name_to_slot(name: str, filaments: list) -> Optional[int]:
    for i, f in enumerate(filaments):
        if f"{f['brand']} - {f['name']}".lower() == name.lower():
            return i + 1
    for i, f in enumerate(filaments):
        if f["name"].lower() in name.lower():
            return i + 1
    return None


def _suggest_layer_heights(nozzle: float) -> list:
    results = []
    for lh_str in ["0.04", "0.08"]:
        lh = float(lh_str)
        if lh <= nozzle * 0.75:
            layer_count = round(6.0 / lh)
            est_hours   = round(layer_count * 0.4 / 60 * 1.4, 1)
            results.append({
                "value":       lh_str,
                "label":       f"{lh_str}mm ({'fine' if lh == 0.04 else 'standard'})",
                "layer_count": layer_count,
                "est_hours":   est_hours,
            })
    return results


def _background_height(layer_height: float) -> float:
    """Return background height as a valid multiple of layer_height (min 7 layers, min 0.56mm).
    Skips layer counts where float division is not exactly integer (e.g. n=7 for 0.08mm)."""
    lh = float(layer_height)
    n = max(7, math.ceil(0.56 / lh))
    while not (round(n * lh, 6) / lh).is_integer():
        n += 1
    return round(n * lh, 6)


def _load_library() -> list:
    if not os.path.exists(LIBRARY_PATH):
        return []
    with open(LIBRARY_PATH) as f:
        return json.load(f)


def _save_library(library: list):
    with open(LIBRARY_PATH, "w") as f:
        json.dump(library, f, indent=2)


def _find_photo_pack() -> Optional[str]:
    for root, dirs, files in os.walk(HUEFORGE_BASE):
        for fname in files:
            if fname == "hue-forge-photo-pack.csv":
                return os.path.join(root, fname)
    return None


# ── Project endpoints ─────────────────────────────────────────────────────────

@app.get("/api/projects")
def list_projects():
    base = Path(HUEFORGE_BASE)
    if not base.exists():
        return []
    projects = []
    for d in sorted(base.iterdir()):
        if not d.is_dir():
            continue
        has_content = any([
            (d / "swap_instructions.txt").exists(),
            (d / "project_file.hfp").exists(),
            (d / "pass2" / "final_model.stl").exists(),
            (d / "final_model.stl").exists(),
        ])
        if has_content:
            projects.append(d.name)
    return projects


@app.get("/api/projects/{project:path}/load")
def load_project(project: str, nozzle: float = 0.4):
    project_dir = os.path.join(HUEFORGE_BASE, project)
    if not os.path.isdir(project_dir):
        raise HTTPException(404, f"Project not found: {project}")

    stl_path  = _resolve_stl(project_dir)
    hfp       = _parse_hfp(project_dir)
    swaps_raw = _parse_swap_instructions(project_dir)
    library   = _load_library()
    library_names = {f"{f['brand']} - {f['name']}".lower() for f in library}
    library_filament_names = {f["name"].lower() for f in library}

    def _in_library(name: str) -> bool:
        n = name.lower()
        if n in library_names:
            return True
        # Also match if any library filament name appears as substring (brand formatting differs)
        return any(lib_name in n for lib_name in library_filament_names if lib_name)

    filaments = hfp["filaments"] if hfp else []
    layer_height_hfp = hfp["layer_height"] if hfp else 0.08

    # Build color changes with slot mapping
    color_changes = []
    unmatched_filaments = []
    if swaps_raw and filaments:
        for swap in swaps_raw["swaps"]:
            slot = _name_to_slot(swap["filament_name"], filaments)
            color = filaments[slot - 1]["color"] if slot else "#000000"
            color_changes.append({
                "top_z":         swap["top_z"],
                "slot":          slot or 1,
                "color":         color,
                "filament_name": swap["filament_name"],
            })
            if not _in_library(swap["filament_name"]):
                if swap["filament_name"] not in unmatched_filaments:
                    unmatched_filaments.append(swap["filament_name"])
        # Also check background filament
        bg = swaps_raw.get("background_filament", "")
        if bg and not _in_library(bg) and bg not in unmatched_filaments:
            unmatched_filaments.append(bg)

    return {
        "project":                  project,
        "stl_path":                 stl_path,
        "stl_found":                stl_path is not None,
        "truck_ref_exists":         os.path.exists(TRUCK_REF),
        "hfp":                      hfp,
        "swap_instructions":        swaps_raw,
        "color_changes":            color_changes,
        "suggested_layer_heights":  _suggest_layer_heights(nozzle),
        "background_height":        _background_height(layer_height_hfp),
        "unmatched_filaments":      unmatched_filaments,
    }


# ── Generate endpoint ─────────────────────────────────────────────────────────

class FilamentSlot(BaseModel):
    color: str
    type:  str = "PLA"

class ColorChange(BaseModel):
    top_z: float
    slot:  int
    color: str

class GenerateRequest(BaseModel):
    project:         str
    nozzle:          float = 0.4
    layer_height:    str   = "0.08"
    filament_slots:  list[FilamentSlot]
    color_changes:   list[ColorChange]


@app.post("/api/generate")
async def generate(req: GenerateRequest):
    if generate_lock.locked():
        raise HTTPException(409, "Generation already in progress")

    project_dir = os.path.join(HUEFORGE_BASE, req.project)
    if not os.path.isdir(project_dir):
        raise HTTPException(404, f"Project not found: {req.project}")

    stl_path = _resolve_stl(project_dir)
    if not stl_path:
        raise HTTPException(422, "No STL found in project directory")
    if not os.path.exists(TRUCK_REF):
        raise HTTPException(422, f"Reference 3MF not found: {TRUCK_REF}")

    dst = os.path.join(HUEFORGE_BASE, req.project, f"{req.project}.3mf")

    filament_colours = [s.color for s in req.filament_slots]
    filament_types   = [s.type  for s in req.filament_slots]
    color_changes    = [(c.top_z, c.slot, c.color) for c in req.color_changes]

    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def log(msg: str):
        loop.call_soon_threadsafe(queue.put_nowait, ("log", msg))

    async def run():
        async with generate_lock:
            try:
                await asyncio.to_thread(
                    make_3mf.generate_3mf,
                    stl_path, TRUCK_REF, dst,
                    req.nozzle, req.layer_height,
                    filament_colours, filament_types, color_changes,
                    log,
                )
                await queue.put(("done", dst))
            except Exception as e:
                await queue.put(("error", str(e)))

    async def stream():
        task = asyncio.create_task(run())
        while True:
            kind, payload = await queue.get()
            if kind == "log":
                yield f"data: {json.dumps({'type': 'log', 'text': payload})}\n\n"
            elif kind == "done":
                yield f"data: {json.dumps({'type': 'done', 'output_path': payload})}\n\n"
                break
            elif kind == "error":
                yield f"data: {json.dumps({'type': 'error', 'message': payload})}\n\n"
                break
        await task

    return StreamingResponse(stream(), media_type="text/event-stream")


# ── RunPod pod helpers ────────────────────────────────────────────────────────

async def _runpod_pod() -> dict:
    query = '''{ pod(input: {podId: "%s"}) {
        id, desiredStatus,
        runtime { ports { ip, isIpPublic, privatePort, publicPort, type } }
        machine { gpuDisplayName }
    } }''' % RUNPOD_POD_ID
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(RUNPOD_GQL,
            headers={"Authorization": f"Bearer {RUNPOD_API_KEY}"},
            json={"query": query})
        r.raise_for_status()
        return r.json().get("data", {}).get("pod") or {}


@app.get("/api/runpod/status")
async def runpod_status():
    if not RUNPOD_API_KEY or not RUNPOD_POD_ID:
        raise HTTPException(503, "RunPod not configured")
    pod = await _runpod_pod()
    if not pod:
        return {"status": "not_found"}
    ssh_host = ssh_port = None
    for p in (pod.get("runtime") or {}).get("ports") or []:
        if p["privatePort"] == 22 and p["isIpPublic"]:
            ssh_host = p["ip"]
            ssh_port = p["publicPort"]
    return {
        "status":    pod.get("desiredStatus", "UNKNOWN").lower(),
        "gpu":       (pod.get("machine") or {}).get("gpuDisplayName"),
        "ssh_host":  ssh_host,
        "ssh_port":  ssh_port,
    }


@app.put("/api/runpod/state")
async def runpod_set_state(body: dict):
    if not RUNPOD_API_KEY or not RUNPOD_POD_ID:
        raise HTTPException(503, "RunPod not configured")
    state = body.get("state")
    if state == "running":
        mutation = 'mutation { podResume(input: {podId: "%s", gpuCount: 1}) { id, desiredStatus } }' % RUNPOD_POD_ID
    else:
        mutation = 'mutation { podStop(input: {podId: "%s"}) { id, desiredStatus } }' % RUNPOD_POD_ID
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(RUNPOD_GQL,
            headers={"Authorization": f"Bearer {RUNPOD_API_KEY}"},
            json={"query": mutation})
        r.raise_for_status()
    return {"ok": True}


def _ssh_connect(ssh_host: str, ssh_port: int) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    key = paramiko.Ed25519Key.from_private_key_file(RUNPOD_SSH_KEY)
    client.connect(ssh_host, port=ssh_port, username="root", pkey=key, timeout=30)
    return client


def _stream_ssh_output(stdout, log):
    """Read SSH stdout, filtering tqdm progress bars, logging meaningful lines."""
    for line in iter(stdout.readline, ""):
        line = line.rstrip()
        if not line:
            continue
        if _TQDM_LINE.match(line):
            continue
        m = _ITER_LINE.match(line)
        if m:
            line = m.group(1)
        log(line)


def _compute_bg_height(layer_height: str, background_height) -> float:
    lh = float(layer_height)
    if background_height is not None:
        return round(background_height, 6)
    n_bg = max(7, math.ceil(0.56 / lh))
    while not (round(n_bg * lh, 6) / lh).is_integer():
        n_bg += 1
    return round(n_bg * lh, 6)


def _filaments_to_csv(filaments: list) -> str:
    """Convert library filament dicts to HueForge CSV string."""
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=["Brand", "Name", "Type", "Color", "TD"])
    writer.writeheader()
    for f in filaments:
        writer.writerow({
            "Brand": f.get("brand", ""),
            "Name":  f.get("name", ""),
            "Type":  f.get("type", "PLA"),
            "Color": f.get("color", "#000000"),
            "TD":    f.get("td", 0),
        })
    return out.getvalue()


# ── New project endpoints ─────────────────────────────────────────────────────

@app.post("/api/projects/create")
async def create_project(
    name:  str        = Form(...),
    image: UploadFile = File(...),
):
    """Create a new project directory and save the uploaded image."""
    safe = re.sub(r'[^\w\s\-.]', '', name).strip()
    if not safe:
        raise HTTPException(422, "Invalid project name")
    project_dir = os.path.join(HUEFORGE_BASE, safe)
    os.makedirs(project_dir, exist_ok=True)
    img_path = os.path.join(project_dir, "image.png")
    content = await image.read()
    with open(img_path, "wb") as f:
        f.write(content)
    return {"project": safe, "image_path": img_path}


class RunAutoforgeRequest(BaseModel):
    project:           str
    backend:           str            = "runpod"  # "runpod" | "local"
    nozzle:            float          = 0.4
    layer_height:      str            = "0.08"
    filaments:         list[dict]     = []   # empty = use full photo pack (pass 1 auto-select)
    max_layers:        int            = 75
    max_swaps:         int            = 8
    max_colors:        int            = 4
    background_height: Optional[float] = None  # if None, auto-compute from layer_height


@app.post("/api/run-autoforge")
async def run_autoforge(req: RunAutoforgeRequest):
    if autoforge_lock.locked():
        raise HTTPException(409, "AutoForge already running")
    if req.backend == "runpod" and (not RUNPOD_API_KEY or not RUNPOD_POD_ID):
        raise HTTPException(503, "RunPod not configured (RUNPOD_API_KEY / RUNPOD_POD_ID missing)")

    project_dir = os.path.join(HUEFORGE_BASE, req.project)
    if not os.path.isdir(project_dir):
        raise HTTPException(404, f"Project not found: {req.project}")

    image_path = os.path.join(project_dir, "image.png")
    if not os.path.exists(image_path):
        raise HTTPException(422, "image.png not found in project directory")

    if req.filaments:
        csv_content = _filaments_to_csv(req.filaments)
    else:
        pack_path = _find_photo_pack()
        if not pack_path:
            raise HTTPException(422, "No filaments provided and photo pack not found")
        with open(pack_path) as f:
            csv_content = f.read()

    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def log(msg: str):
        loop.call_soon_threadsafe(queue.put_nowait, ("log", msg))

    def _run_runpod():
        ssh = None
        try:
            def _gql(client, query):
                r = client.post(RUNPOD_GQL,
                    headers={"Authorization": f"Bearer {RUNPOD_API_KEY}"},
                    json={"query": query})
                r.raise_for_status()
                body = r.json()
                if body.get("errors"):
                    raise RuntimeError(body["errors"][0]["message"])
                return body.get("data", {})

            _pod_query = '''{ pod(input: {podId: "%s"}) {
                desiredStatus,
                runtime { ports { ip, isIpPublic, privatePort, publicPort } }
            } }''' % RUNPOD_POD_ID

            def _parse_ssh(pod):
                for p in (pod.get("runtime") or {}).get("ports") or []:
                    if p["privatePort"] == 22 and p["isIpPublic"]:
                        return p["ip"], p["publicPort"]
                return None, None

            with httpx.Client(timeout=15) as client:
                pod = _gql(client, _pod_query).get("pod") or {}
                if not pod:
                    raise RuntimeError("Pod not found — check RUNPOD_POD_ID")

                if pod["desiredStatus"] != "RUNNING":
                    log("Pod is stopped — starting...")
                    _gql(client, 'mutation { podResume(input: {podId: "%s", gpuCount: 1}) { id } }' % RUNPOD_POD_ID)
                    ssh_host = ssh_port = None
                    for attempt in range(36):  # up to 3 minutes
                        time.sleep(5)
                        pod = _gql(client, _pod_query).get("pod") or {}
                        ssh_host, ssh_port = _parse_ssh(pod)
                        if pod.get("desiredStatus") == "RUNNING" and ssh_host:
                            log(f"Pod ready ({ssh_host}:{ssh_port})")
                            break
                        log(f"Waiting for pod... ({(attempt + 1) * 5}s elapsed)")
                    else:
                        raise RuntimeError("Pod did not start within 3 minutes")
                else:
                    ssh_host, ssh_port = _parse_ssh(pod)
                    if not ssh_host:
                        raise RuntimeError("Pod SSH port not available yet — try again in a moment")

            log(f"Connecting to RunPod pod ({ssh_host}:{ssh_port})...")
            ssh = _ssh_connect(ssh_host, ssh_port)

            remote_proj = f"/workspace/{req.project}"
            log(f"Setting up remote project: {remote_proj}")
            ssh.exec_command(f"mkdir -p '{remote_proj}/pass2'")[1].read()

            # Pin torch/cuDNN to versions known to work on RunPod RTX 5090 pods (CUDA 12.8).
            # AutoForge's resolver pulls cu130 by default which fails on these hosts.
            log("Installing dependencies...")
            for pkg_cmd in [
                ("pip install -q --break-system-packages "
                 "'torch==2.9.1+cu128' 'torchvision==0.24.1+cu128' "
                 "--index-url https://download.pytorch.org/whl/cu128 2>&1"),
                ("pip install -q --break-system-packages 'nvidia-cudnn-cu12==9.19.0.56' 2>&1"),
                ("pip install -q --break-system-packages AutoForge 2>&1"),
            ]:
                _, out, _ = ssh.exec_command(pkg_cmd)
                out.read()
            autoforge_bin = "/usr/local/bin/autoforge"
            log(f"AutoForge ready at {autoforge_bin}")

            # Re-open SFTP after dep install — session can go stale during long pip runs
            sftp = ssh.open_sftp()

            log("Uploading image...")
            sftp.put(image_path, f"{remote_proj}/image.png")

            log("Uploading filament CSV...")
            with sftp.open(f"{remote_proj}/filaments.csv", "w") as rf:
                rf.write(csv_content)

            bg_h = _compute_bg_height(req.layer_height, req.background_height)
            inner = (
                f"{autoforge_bin}"
                f" --input_image {remote_proj}/image.png"
                f" --csv_file {remote_proj}/filaments.csv"
                f" --max_layers {req.max_layers}"
                f" --pruning_max_swaps {req.max_swaps}"
                f" --pruning_max_colors {req.max_colors}"
                f" --layer_height {req.layer_height}"
                f" --background_height {bg_h}"
                f" --nozzle_diameter {req.nozzle}"
                f" --output_folder {remote_proj}/pass2"
                f" 2>&1 | tee {remote_proj}/pass2/run.log"
            )
            cmd = f"bash -c 'set -o pipefail; {inner}'"
            log(f"Running AutoForge on RunPod (nozzle={req.nozzle}mm, layer={req.layer_height}mm, bg={bg_h}mm)...")
            _, stdout, _ = ssh.exec_command(cmd, get_pty=True)
            _stream_ssh_output(stdout, log)

            if stdout.channel.recv_exit_status() != 0:
                raise RuntimeError("AutoForge exited with non-zero status")

            log("Downloading results...")
            pass2_local = os.path.join(project_dir, "pass2")

            def _sftp_get_dir(remote_dir, local_dir):
                os.makedirs(local_dir, exist_ok=True)
                for entry in sftp.listdir_attr(remote_dir):
                    rpath = f"{remote_dir}/{entry.filename}"
                    lpath = os.path.join(local_dir, entry.filename)
                    if stat.S_ISDIR(entry.st_mode):
                        _sftp_get_dir(rpath, lpath)
                    else:
                        sftp.get(rpath, lpath)

            _sftp_get_dir(f"{remote_proj}/pass2", pass2_local)

            for fname in ["project_file.hfp", "swap_instructions.txt"]:
                src = os.path.join(pass2_local, fname)
                dst = os.path.join(project_dir, fname)
                if os.path.exists(src):
                    shutil.copy(src, dst)
                    log(f"Copied {fname} to project root")
                else:
                    log(f"Warning: {fname} not found in pass2 ({src})")

            sftp.close()
            loop.call_soon_threadsafe(queue.put_nowait, ("done", req.project))

        except Exception as e:
            loop.call_soon_threadsafe(queue.put_nowait, ("error", str(e)))
        finally:
            if ssh:
                ssh.close()

    def _run_local():
        ssh = None
        sd_unloaded = False
        try:
            # Unload SD model to free VRAM before running AutoForge
            with httpx.Client(timeout=30) as hc:
                try:
                    r = hc.post(f"{SD_API_URL}/sdapi/v1/unload-checkpoint")
                    if r.status_code == 200:
                        log("SD model unloaded — VRAM freed for AutoForge.")
                        sd_unloaded = True
                    else:
                        log(f"Warning: SD unload returned {r.status_code}, continuing anyway.")
                except Exception as e:
                    log(f"Warning: could not unload SD model ({e}), continuing anyway.")

            # Files are on the shared mount — write CSV directly, no SFTP needed
            csv_path = os.path.join(project_dir, "filaments.csv")
            with open(csv_path, "w") as f:
                f.write(csv_content)

            log(f"Connecting to local GPU host ({LOCAL_GPU_HOST})...")
            ssh = _ssh_connect(LOCAL_GPU_HOST, 22)

            # Install AutoForge if not present (persists on host between runs)
            LOCAL_AF_BIN = "/usr/local/bin/autoforge"
            _, out, _ = ssh.exec_command(f"test -f {LOCAL_AF_BIN} && echo OK || echo MISSING")
            if out.read().decode().strip() != "OK":
                log("Installing AutoForge (first time, ~3 min)...")
                for pkg_cmd in [
                    "apt-get install -y python3-pip 2>&1",
                    ("python3 -m pip install --break-system-packages "
                     "'torch==2.9.1+cu128' 'torchvision==0.24.1+cu128' "
                     "--index-url https://download.pytorch.org/whl/cu128 2>&1"),
                    "python3 -m pip install --break-system-packages 'nvidia-cudnn-cu12==9.19.0.56' 2>&1",
                    "python3 -m pip install --break-system-packages AutoForge 2>&1",
                ]:
                    _, out, _ = ssh.exec_command(pkg_cmd)
                    for line in iter(out.readline, ""):
                        line = line.rstrip()
                        if line:
                            log(line)
                # Verify install succeeded
                _, out, _ = ssh.exec_command(f"test -f {LOCAL_AF_BIN} && echo OK || echo MISSING")
                if out.read().decode().strip() != "OK":
                    raise RuntimeError("AutoForge installation failed — check VM 101 manually")
                log("AutoForge ready.")
            else:
                log("AutoForge found.")

            # Project files live at /mnt/media/claude/hueforge/<project>/ on the host
            host_proj = f"/mnt/media/claude/hueforge/{req.project}"
            host_pass2 = f"{host_proj}/pass2"
            ssh.exec_command(f"mkdir -p '{host_pass2}'")[1].read()

            bg_h = _compute_bg_height(req.layer_height, req.background_height)
            inner = (
                f"{LOCAL_AF_BIN}"
                f" --input_image {host_proj}/image.png"
                f" --csv_file {host_proj}/filaments.csv"
                f" --max_layers {req.max_layers}"
                f" --pruning_max_swaps {req.max_swaps}"
                f" --pruning_max_colors {req.max_colors}"
                f" --layer_height {req.layer_height}"
                f" --background_height {bg_h}"
                f" --nozzle_diameter {req.nozzle}"
                f" --output_folder {host_pass2}"
                f" 2>&1 | tee {host_pass2}/run.log"
            )
            cmd = f"bash -c 'set -o pipefail; {inner}'"
            log(f"Running AutoForge on local A2000 (nozzle={req.nozzle}mm, layer={req.layer_height}mm, bg={bg_h}mm)...")
            _, stdout, _ = ssh.exec_command(cmd, get_pty=True)
            _stream_ssh_output(stdout, log)

            if stdout.channel.recv_exit_status() != 0:
                raise RuntimeError("AutoForge exited with non-zero status")

            # Results are already on the mounted filesystem — just copy hfp/swap to project root
            for fname in ["project_file.hfp", "swap_instructions.txt"]:
                src = os.path.join(project_dir, "pass2", fname)
                dst = os.path.join(project_dir, fname)
                if os.path.exists(src):
                    shutil.copy(src, dst)
                    log(f"Copied {fname} to project root")
                else:
                    log(f"Warning: {fname} not found in pass2")

            loop.call_soon_threadsafe(queue.put_nowait, ("done", req.project))

        except Exception as e:
            loop.call_soon_threadsafe(queue.put_nowait, ("error", str(e)))
        finally:
            if ssh:
                ssh.close()
            if sd_unloaded:
                log("Reloading SD model...")
                with httpx.Client(timeout=60) as hc:
                    try:
                        hc.post(f"{SD_API_URL}/sdapi/v1/reload-checkpoint")
                        log("SD model reloaded.")
                    except Exception as e:
                        log(f"Warning: SD reload failed ({e}) — reload manually at {SD_API_URL}")

    def _run_in_thread():
        if req.backend == "local":
            _run_local()
        else:
            _run_runpod()

    async def run():
        async with autoforge_lock:
            await asyncio.to_thread(_run_in_thread)

    async def stream():
        task = asyncio.create_task(run())
        while True:
            try:
                kind, payload = await asyncio.wait_for(queue.get(), timeout=20.0)
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
                continue
            if kind == "log":
                yield f"data: {json.dumps({'type': 'log', 'text': payload})}\n\n"
            elif kind == "done":
                yield f"data: {json.dumps({'type': 'done', 'project': payload})}\n\n"
                break
            elif kind == "error":
                yield f"data: {json.dumps({'type': 'error', 'message': payload})}\n\n"
                break
        await task

    return StreamingResponse(stream(), media_type="text/event-stream")


# ── Library endpoints ─────────────────────────────────────────────────────────

class FilamentEntry(BaseModel):
    brand: str
    name:  str
    type:  str = "PLA"
    color: str = "#000000"
    td:    float = 0.0


@app.get("/api/library")
def get_library():
    return _load_library()


@app.post("/api/library")
def upsert_filament(entry: FilamentEntry):
    library = _load_library()
    key = (entry.brand.lower(), entry.name.lower())
    for i, f in enumerate(library):
        if (f["brand"].lower(), f["name"].lower()) == key:
            library[i] = entry.dict()
            _save_library(library)
            return library
    library.append(entry.dict())
    _save_library(library)
    return library


@app.delete("/api/library/{brand}/{name}")
def delete_filament(brand: str, name: str):
    library = _load_library()
    library = [f for f in library
               if not (f["brand"].lower() == brand.lower()
                       and f["name"].lower() == name.lower())]
    _save_library(library)
    return library


class ImportRequest(BaseModel):
    filaments: list[FilamentEntry]

@app.post("/api/library/import")
def import_filaments(req: ImportRequest):
    library = _load_library()
    existing = {(f["brand"].lower(), f["name"].lower()): i for i, f in enumerate(library)}
    for entry in req.filaments:
        key = (entry.brand.lower(), entry.name.lower())
        if key in existing:
            library[existing[key]] = entry.dict()
        else:
            library.append(entry.dict())
    _save_library(library)
    return library


@app.get("/api/filament-pack")
def get_filament_pack():
    pack_path = _find_photo_pack()
    if not pack_path:
        raise HTTPException(404, "hue-forge-photo-pack.csv not found")
    library   = _load_library()
    lib_keys  = {(f["brand"].lower(), f["name"].lower()) for f in library}
    results   = []
    with open(pack_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            brand = row.get("Brand", "").strip()
            name  = row.get("Name", "").strip()
            if not brand or not name:
                continue
            results.append({
                "brand":  brand,
                "name":   name,
                "type":   row.get("Type", "PLA").strip(),
                "color":  row.get("Color", "#000000").strip(),
                "td":     float(row.get("TD", 0) or 0),
                "in_library": (brand.lower(), name.lower()) in lib_keys,
            })
    return results


# ── Public file downloads ─────────────────────────────────────────────────────

@app.get("/hue-forge-photo-pack.csv")
def download_photo_pack():
    pack_path = _find_photo_pack()
    if not pack_path:
        raise HTTPException(404, "hue-forge-photo-pack.csv not found")
    return FileResponse(
        pack_path,
        media_type="text/csv",
        filename="hue-forge-photo-pack.csv",
    )


# ── Static frontend ───────────────────────────────────────────────────────────

app.mount("/", StaticFiles(directory="static", html=True), name="static")
