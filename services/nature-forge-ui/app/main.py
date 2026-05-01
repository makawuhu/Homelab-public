import asyncio
import io
import json
import os
import re
import shutil
import tempfile
import uuid

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image
from starlette.background import BackgroundTask
import httpx

import make_3mf

GPU_API = os.getenv("GPU_API_URL", "http://192.168.x.167:8080")
FILE_SERVER = os.getenv("FILE_SERVER_URL", "http://192.168.x.167:8081")
NF_IMAGE = os.getenv("NF_IMAGE", "nature-forge-worker:local")
OUTPUT_BASE_URL = os.getenv("OUTPUT_BASE_URL", "https://gpu-outputs.yourdomain.com")
TRUCK_REF = os.getenv("TRUCK_REF_PATH", "/data/hueforge/Truckee river test/truckee-river_Front_200x133.3mf")

PRESETS = [
    {"name": "polymaker-photo",        "label": "Polymaker Photo Color Pack"},
    {"name": "polymaker-photo-bw",     "label": "Polymaker Photo B&W"},
    {"name": "polymaker-nature",       "label": "Polymaker Nature Color Set"},
    {"name": "polymaker-fire",         "label": "Polymaker Fire Color Set"},
    {"name": "polymaker-water",        "label": "Polymaker Water Color Set"},
    {"name": "polymaker-blue",         "label": "Polymaker Blue Starter Pack"},
    {"name": "polymaker-red",          "label": "Polymaker Red Starter Pack"},
    {"name": "polymaker-green",        "label": "Polymaker Green Starter Pack"},
    {"name": "polymaker-standard",     "label": "Polymaker Standard Pack"},
    {"name": "polymaker-professional", "label": "Polymaker Professional Pack"},
    {"name": "polymaker-color",        "label": "Polymaker Color Pack"},
]

# All unique filaments across all Polymaker presets
FILAMENT_COLORS = {
    "Polymaker - Panchroma Matte Charcoal Black": "#2F2E30",
    "Polymaker - PolyLite Grey":                  "#8B8E96",
    "Polymaker - PolyLite Natural":               "#DFD3C3",
    "Polymaker - PolyLite White":                 "#DDD7D3",
    "Polymaker - PolyLite Lemon Yellow":          "#EED230",
    "Polymaker - PolyLite Lime Green":            "#D5D701",
    "Polymaker - PolyLite Azure Blue":            "#0061D5",
    "Polymaker - PolyLite Aqua Blue":             "#5EBDDB",
    "Polymaker - PolyLite Red":                   "#D90102",
    "Polymaker - PolyLite Pro Light Red":         "#DC605A",
    "Polymaker - PolyLite Orange":                "#F36201",
    "Polymaker - PolyLite Green":                 "#30A45F",
    "Polymaker - PolyLite Jungle Green":          "#4E742D",
    "Polymaker - PolyLite Blue":                  "#013178",
    "Polymaker - Panchroma Matte Army Brown":     "#795A4D",
}

RUN_CMD = (
    "python3 -c '"
    "import json,os,subprocess,sys; "
    'open("/tmp/job.json","w").write(os.environ["JOB_JSON"]); '
    'sys.exit(subprocess.run(["python3","-m","nature_forge.worker","--job","/tmp/job.json","--workspace","/tmp"]).returncode)'
    "'"
)

app = FastAPI(title="Nature-Forge UI")


def _parse_swap_instructions_text(text: str):
    start_match = re.search(r'Start with (.+?)(?:,|$)', text, re.MULTILINE)
    start_filament = start_match.group(1).strip() if start_match else ""
    swaps = []
    for m in re.finditer(r'At layer #(\d+) \(([\d.]+)mm\) swap to (.+)', text):
        swaps.append({
            "layer":         int(m.group(1)),
            "top_z":         float(m.group(2)),
            "filament_name": m.group(3).strip().rstrip('.'),
        })
    return start_filament, swaps


def _build_filament_args(start_filament: str, swaps: list, max_slots: int = 4):
    slot_map = {}
    slot_colors = []
    slot_types = []

    def add_slot(name):
        if name not in slot_map and len(slot_map) < max_slots:
            slot_map[name] = len(slot_map) + 1
            slot_colors.append(FILAMENT_COLORS.get(name, "#000000"))
            slot_types.append("PLA")

    if start_filament:
        add_slot(start_filament)
    for swap in swaps:
        add_slot(swap["filament_name"])

    while len(slot_colors) < max_slots:
        slot_colors.append(slot_colors[-1] if slot_colors else "#000000")
        slot_types.append("PLA")

    color_changes = [
        (s["top_z"], slot_map.get(s["filament_name"], 1), FILAMENT_COLORS.get(s["filament_name"], "#000000"))
        for s in swaps
    ]

    return slot_colors[:max_slots], slot_types[:max_slots], color_changes


@app.get("/api/packs")
async def get_packs():
    return {"packs": PRESETS}


@app.get("/api/health")
async def health():
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{GPU_API}/health")
            return resp.json()
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.post("/api/jobs")
async def submit_job(
    image: UploadFile = File(...),
    preset: str = Form(...),
    layer_height: float = Form(0.08),
    base_layer_height: float = Form(0.16),
    base_thickness: float = Form(0.64),
    max_mesh_height: float = Form(1.76),
    print_width: float = Form(150.0),
    detail_size: float = Form(0.4),
    max_swaps: int = Form(8),
    max_colors: int = Form(4),
    iterations: int = Form(1000),
    exposure: float = Form(0.0),
    midtone_lift: float = Form(0.0),
    no_pruning: bool = Form(False),
):
    job_uuid = str(uuid.uuid4())

    image_data = await image.read()
    ext = os.path.splitext(image.filename or "image.png")[1].lower() or ".png"

    if exposure != 0.0 or midtone_lift != 0.0:
        import math
        lut = [(i / 255.0) ** (2.0 ** (-exposure)) * 255.0 for i in range(256)]
        if midtone_lift != 0.0:
            lut = [v + midtone_lift * math.sin(math.pi * i / 255) * 80 for i, v in enumerate(lut)]
        lut = bytes([min(255, max(0, round(v))) for v in lut] * 3)
        img = Image.open(io.BytesIO(image_data)).convert("RGB").point(lut)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        image_data = buf.getvalue()
        ext = ".png"

    img_filename = f"{job_uuid}-input{ext}"

    async with httpx.AsyncClient(timeout=30) as client:
        up = await client.put(f"{FILE_SERVER}/{img_filename}", content=image_data)
        if up.status_code >= 400:
            raise HTTPException(status_code=502, detail="Image upload to file server failed")

    image_url = f"{FILE_SERVER}/{img_filename}"
    base_layer_count = round(base_thickness / layer_height)
    blend_depth = round(max_mesh_height / layer_height)

    job = {
        "input_image": image_url,
        "preset": preset,
        "cli_args": {
            "layer_height": layer_height,
            "base_layer": base_layer_count,
            "width": print_width,
            "blend_depth": blend_depth,
            "detail_size": detail_size,
            "pruning_max_swaps": max_swaps,
            "pruning_max_colors": max_colors,
            "iterations": iterations,
            "visualize": True,
            "perform_pruning": not no_pruning,
            "fast_pruning": not no_pruning,
        },
    }

    gpu_payload = {
        "job_type": "custom_docker",
        "payload": {
            "image": NF_IMAGE,
            "command": RUN_CMD,
            "env": {"JOB_JSON": json.dumps(job)},
            "volumes": {f"/opt/outputs/{job_uuid}": "/tmp/output"},
            "shm_size": "4g",
        },
        "timeout_seconds": 1800,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{GPU_API}/jobs", json=gpu_payload)
        resp.raise_for_status()
        gpu_job = resp.json()

    return {
        "job_id":     gpu_job["job_id"],
        "job_uuid":   job_uuid,
        "output_url": f"{OUTPUT_BASE_URL}/{job_uuid}",
    }


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{GPU_API}/jobs/{job_id}")
        resp.raise_for_status()
        return resp.json()


# ── Async 3MF export ──────────────────────────────────────────────────────────
# POST /api/export-3mf/{uuid}  → starts background job, returns export_id
# GET  /api/export-3mf/status/{export_id} → poll until done
# GET  /api/export-3mf/download/{export_id} → download completed file

_exports: dict = {}  # export_id → {status, path, tmpdir, filename, error}


async def _run_export(export_id: str, job_uuid: str, nozzle: float, layer_height: str, simplify_faces: int = 0):
    exp = _exports[export_id]
    base_url = f"{OUTPUT_BASE_URL}/{job_uuid}"
    tmpdir = tempfile.mkdtemp()
    exp["tmpdir"] = tmpdir

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            swap_r = await client.get(f"{base_url}/swap_instructions.txt")
            swap_r.raise_for_status()

        start_filament, swaps = _parse_swap_instructions_text(swap_r.text)
        filament_colours, filament_types, color_changes = _build_filament_args(start_filament, swaps)

        stl_path = os.path.join(tmpdir, "model.stl")
        dst_path = os.path.join(tmpdir, "output.3mf")

        async with httpx.AsyncClient(timeout=600) as client:
            async with client.stream("GET", f"{base_url}/final_model.stl") as r:
                r.raise_for_status()
                with open(stl_path, "wb") as f:
                    async for chunk in r.aiter_bytes(65536):
                        f.write(chunk)

        truck_ref = TRUCK_REF if os.path.exists(TRUCK_REF) else None
        await asyncio.to_thread(
            make_3mf.generate_3mf,
            stl_path=stl_path,
            dst=dst_path,
            nozzle=nozzle,
            layer_height=layer_height,
            filament_colours=filament_colours,
            filament_types=filament_types,
            color_changes=color_changes,
            truck_ref=truck_ref,
            simplify_faces=simplify_faces,
        )

        exp["path"]   = dst_path
        exp["status"] = "done"

    except Exception as e:
        exp["status"] = "failed"
        exp["error"]  = str(e)
        shutil.rmtree(tmpdir, ignore_errors=True)
        exp["tmpdir"] = None


@app.post("/api/export-3mf/{job_uuid}")
async def start_export_3mf(job_uuid: str, nozzle: float = 0.4, layer_height: str = "0.08", simplify_faces: int = 0):
    export_id = str(uuid.uuid4())
    _exports[export_id] = {
        "status":   "pending",
        "path":     None,
        "tmpdir":   None,
        "filename": f"nature-forge-{job_uuid[:8]}.3mf",
        "error":    None,
    }
    asyncio.create_task(_run_export(export_id, job_uuid, nozzle, layer_height, simplify_faces))
    return {"export_id": export_id, "status": "pending"}


@app.get("/api/export-3mf/status/{export_id}")
async def export_status(export_id: str):
    if export_id not in _exports:
        raise HTTPException(status_code=404, detail="Export not found")
    exp = _exports[export_id]
    return {"status": exp["status"], "error": exp["error"]}


@app.get("/api/export-3mf/download/{export_id}")
async def download_export(export_id: str):
    if export_id not in _exports:
        raise HTTPException(status_code=404, detail="Export not found")
    exp = _exports[export_id]
    if exp["status"] != "done":
        raise HTTPException(status_code=409, detail="Export not ready")

    def cleanup():
        _exports.pop(export_id, None)
        if exp["tmpdir"]:
            shutil.rmtree(exp["tmpdir"], ignore_errors=True)

    return FileResponse(
        exp["path"],
        media_type="application/octet-stream",
        filename=exp["filename"],
        background=BackgroundTask(cleanup),
    )


app.mount("/", StaticFiles(directory="static", html=True), name="static")
