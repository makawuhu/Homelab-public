# HueForge Pipeline

End-to-end pipeline: image → AutoForge on vast.ai V100 → BambuStudio 3MF for Bambu X1C.

Future plan: turn into a standalone Python project (`hueforge-pipeline`).

## Infrastructure

- **vast.ai**: GPU compute (Tesla V100 SXM2 16GB)
- **VM 101** (`192.168.x.5`): FileBrowser, output storage at `/mnt/media/claude/hueforge/`
- **claude-ops LXC** (`192.168.x.8`): orchestration, `vastai-stop` / `vastai-status` scripts
- **API key**: `/root/.secrets/vastai`

## Vast.ai Instance Setup (each new instance)

1. Add Claude's SSH key to `~/.ssh/authorized_keys`:
   ```
   ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIN6xB7nxgGkabXDNYLD/eLKlvVnASos/FVbR/RBjiS8Z claude-ops@yourhostname
   ```

2. Fix PyTorch CUDA mismatch (instances ship with cu130, driver supports cu126):
   ```bash
   pip install --force-reinstall torch --index-url https://download.pytorch.org/whl/cu126
   python3 -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
   ```

3. Install AutoForge (hvoss-techfak, NOT cubiq):
   ```bash
   pip install AutoForge
   ```

## Workflow

### Pass 1 — Filament Discovery

Run AutoForge against the full photo pack to find the best filaments:

```bash
tmux new-session -d -s autoforge "autoforge \
  --input_image /mnt/media/claude/hueforge/<project>/image.png \
  --csv_file /mnt/media/claude/hueforge/hue-forge-photo-pack.csv \
  --max_layers <N> --pruning_max_swaps <S> --layer_height <H> --background_height 0.56 \
  --output_folder /mnt/media/claude/hueforge/<project>/pass1 \
  2>&1 | tee /mnt/media/claude/hueforge/<project>/pass1/run.log"
```

Read `pass1/swap_instructions.txt` to identify the selected filaments.

### Pass 2 — Constrained Optimisation

Create a `filaments.csv` with only the identified filaments, re-run:

```bash
tmux new-session -d -s autoforge2 "autoforge \
  --input_image /mnt/media/claude/hueforge/<project>/image.png \
  --csv_file /mnt/media/claude/hueforge/<project>/filaments.csv \
  --max_layers <N> --pruning_max_swaps <S> --layer_height <H> --background_height 0.56 \
  --output_folder /mnt/media/claude/hueforge/<project>/pass2 \
  2>&1 | tee /mnt/media/claude/hueforge/<project>/pass2/run.log"
```

### 3MF Generation

**Must run on vast.ai** — the claude-ops LXC doesn't have enough RAM for the geometry XML (126–195 MB).

Script: `make_3mf.py` (see below). Requires `trimesh` (already on vast.ai instances).

```bash
python3 make_3mf.py
```

Copy the truckee reference 3MF to vast.ai each session:
```bash
scp -P <port> /tmp/truckee_ref.3mf root@ssh3.vast.ai:/tmp/
```

Reference file location on VM 101:
`/mnt/media/claude/hueforge/Truckee river test/truckee-river_Front_200x133.3mf`

### Teardown

```bash
vastai-stop   # destroys the instance via API
```

## BambuStudio 3MF Format

BambuStudio ignores metadata from non-native 3MF files. The file must mimic the exact native structure.

### Required Files

| File | Purpose |
|------|---------|
| `3D/3dmodel.model` | Thin component reference — **no geometry** |
| `3D/Objects/object_1.model` | Mesh geometry (STL → 3MF XML) |
| `3D/_rels/3dmodel.model.rels` | Relationship pointing to object_1.model |
| `Metadata/custom_gcode_per_layer.xml` | **Color changes** |
| `Metadata/project_settings.config` | Printer/filament JSON (from real reference) |
| `Metadata/model_settings.config` | Object and plate metadata |

### Color Change Format

```xml
<?xml version="1.0" encoding="utf-8"?>
<custom_gcodes_per_layer>
<plate>
<plate_info id="1"/>
<layer top_z="4.24" type="2" extruder="2" color="#8c9099" extra="" gcode="tool_change"/>
<layer top_z="4.96" type="2" extruder="1" color="#1c1c1c" extra="" gcode="tool_change"/>
<mode value="MultiAsSingle"/>
</plate>
</custom_gcodes_per_layer>
```

- `top_z`: height in mm at the **top** of the layer where the swap occurs
- `extruder`: 1-indexed filament slot
- `MultiAsSingle`: manual swap mode (no AMS)
- **Use max 4 filament slots** — extending to 5 breaks BambuStudio's per-filament array parsing
- Reuse slot 1 for repeat filaments (e.g. Charcoal Black used twice → still slot 1)

### Z Offset

Use `abs(mesh.bounds[0][2])` from trimesh as the Z translation in the build item `transform` attribute.

## Print Settings (X1C)

| Setting | Value |
|---------|-------|
| Layer height | 0.04mm or 0.08mm (per job) |
| First layer | 0.24mm |
| Infill | 100% |
| Plate | Textured PEI |
| Nozzle | 0.4mm |
| Mode | MultiAsSingle (manual swap, no AMS) |

## Filament CSV Format

```csv
Brand, Type, Color, Name, TD, Tags, Secondary_Type, Secondary_Color, Secondary_Strength, Owned, Uuid
PolyTerra,PLA,#1c1c1c,Charcoal Black,0.3,,None,#0000ff,0,FALSE,{2590d566-07e4-4828-9c13-4d6b39192c71}
PolyLite,PLA,#e8e6d0,Natural,21,,None,#0000ff,0,FALSE,{8bcb2c01-32eb-81f3-382d-0182d6acafed}
```

Full photo pack: `/mnt/media/claude/hueforge/mountain_v1/hue-forge-photo-pack.csv` on VM 101.
