"""
make_3mf.py — Manual/vast.ai version for one-off use. Edit CONFIG section and run directly.

NOTE: services/autoforge-ui/app/make_3mf.py is the canonical version used by the web UI.

make_3mf.py — Generate a BambuStudio-native 3MF from an AutoForge STL output.

Must run on vast.ai (requires trimesh + sufficient RAM for geometry XML).
Requires a real BambuStudio 3MF as a structural template (truckee_ref.3mf).

Usage:
  Edit the CONFIG section and run: python3 make_3mf.py
"""
import trimesh, zipfile, json, os

# ── CONFIG ────────────────────────────────────────────────────────────────────
STL_PATH      = '/mnt/media/claude/hueforge/<project>/pass2/final_model.stl'
TRUCK_REF     = '/tmp/truckee_ref.3mf'   # real BambuStudio 3MF as template
DST           = '/mnt/media/claude/hueforge/<project>/output.3mf'

NOZZLE        = 0.4      # 0.4 or 0.2 — drives FIRST_LAYER + all speed/accel settings
LAYER_HEIGHT  = '0.08'   # mm — must match AutoForge --layer_height

# AutoForge --background_height should be >= 0.56mm (7 layers at 0.08mm).
# 0.24mm (3 layers) is too thin on large prints — left side misses the bed.

# 4 filament slots max. Reuse slot 1 for repeat filaments.
FILAMENT_COLOURS = ['#1c1c1c', '#8c9099', '#e2dedb', '#e8e6d0']
FILAMENT_TYPES   = ['PLA',     'PLA',     'PLA',     'PLA'    ]

# Color changes: (top_z_mm, extruder_slot_1indexed, hex_color)
# top_z = height at TOP of the layer where swap occurs (from swap_instructions.txt)
COLOR_CHANGES = [
    (4.24, 2, '#8c9099'),
    (4.96, 1, '#1c1c1c'),
    (5.28, 2, '#8c9099'),
    (5.44, 1, '#1c1c1c'),
    (5.52, 3, '#e2dedb'),
    (5.76, 1, '#1c1c1c'),
    (5.84, 2, '#8c9099'),
    (5.92, 3, '#e2dedb'),
]
# ── END CONFIG ────────────────────────────────────────────────────────────────

print("Loading STL...")
mesh = trimesh.load(STL_PATH)
min_z      = float(mesh.bounds[0][2])
face_count = len(mesh.faces)
print(f"  Faces: {face_count}, min Z: {min_z:.4f}")

print("Building geometry XML...")
lines = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">',
    '  <resources>', '    <object id="1" type="model">', '      <mesh>', '        <vertices>',
]
for v in mesh.vertices:
    lines.append(f'          <vertex x="{v[0]:.6f}" y="{v[1]:.6f}" z="{v[2]:.6f}"/>')
lines.append('        </vertices>\n        <triangles>')
for f in mesh.faces:
    lines.append(f'          <triangle v1="{f[0]}" v2="{f[1]}" v3="{f[2]}"/>')
lines += ['        </triangles>', '      </mesh>', '    </object>', '  </resources>', '</model>']
geom_xml = '\n'.join(lines)
print(f"  {len(geom_xml)/1024/1024:.1f} MB")

z = abs(min_z)

thin_3dmodel = f'''<?xml version="1.0" encoding="UTF-8"?>
<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p">
 <metadata name="Application">BambuStudio-02.05.00.66</metadata>
 <metadata name="BambuStudio:3mfVersion">1</metadata>
 <metadata name="CreationDate">2026-04-05</metadata>
 <metadata name="ModificationDate">2026-04-05</metadata>
 <resources>
  <object id="2" p:UUID="00000001-61cb-4c03-9d28-80fed5dfa1dc" type="model">
   <components>
    <component p:path="/3D/Objects/object_1.model" objectid="1" p:UUID="00010000-b206-40ff-9872-83e8017abed1" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>
   </components>
  </object>
 </resources>
 <build p:UUID="2c7c17d8-22b5-4d84-8835-1976022ea369">
  <item objectid="2" p:UUID="00000002-b1ec-4553-aec9-835e5b724bb4" transform="1 0 0 0 1 0 0 0 1 128 128 {z:.10f}" printable="1"/>
 </build>
</model>'''

custom_gcode_xml = '<?xml version="1.0" encoding="utf-8"?>\n<custom_gcodes_per_layer>\n<plate>\n<plate_info id="1"/>\n'
for top_z, extruder, color in COLOR_CHANGES:
    custom_gcode_xml += f'<layer top_z="{top_z}" type="2" extruder="{extruder}" color="{color}" extra="" gcode="tool_change"/>\n'
custom_gcode_xml += '<mode value="MultiAsSingle"/>\n</plate>\n</custom_gcodes_per_layer>'

model_settings = f'''<?xml version="1.0" encoding="UTF-8"?>
<config>
  <object id="2">
    <metadata key="name" value="hueforge_model"/>
    <metadata key="extruder" value="1"/>
    <metadata face_count="{face_count}"/>
    <part id="1" subtype="normal_part">
      <metadata key="name" value="hueforge_model"/>
      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>
      <metadata key="source_file" value="hueforge_model.stl"/>
      <metadata key="source_object_id" value="0"/>
      <metadata key="source_volume_id" value="0"/>
      <metadata key="source_offset_x" value="0"/>
      <metadata key="source_offset_y" value="0"/>
      <metadata key="source_offset_z" value="{z:.10f}"/>
      <mesh_stat face_count="{face_count}" edges_fixed="0" degenerate_facets="0" facets_removed="0" facets_reversed="0" backwards_edges="0"/>
    </part>
  </object>
  <plate>
    <metadata key="plater_id" value="1"/>
    <metadata key="plater_name" value=""/>
    <metadata key="locked" value="false"/>
    <metadata key="filament_map_mode" value="Auto For Flush"/>
    <metadata key="filament_maps" value="1 1 1 1"/>
    <metadata key="thumbnail_file" value="Metadata/plate_1.png"/>
    <metadata key="thumbnail_no_light_file" value="Metadata/plate_no_light_1.png"/>
    <metadata key="top_file" value="Metadata/top_1.png"/>
    <metadata key="pick_file" value="Metadata/pick_1.png"/>
    <model_instance>
      <metadata key="object_id" value="2"/>
      <metadata key="instance_id" value="0"/>
      <metadata key="identify_id" value="124"/>
    </model_instance>
  </plate>
  <assemble>
   <assemble_item object_id="2" instance_id="0" transform="1 0 0 0 1 0 0 0 1 128 128 {z:.10f}" offset="0 0 0" />
  </assemble>
</config>'''

with zipfile.ZipFile(TRUCK_REF) as zt:
    proj = json.loads(zt.read('Metadata/project_settings.config'))

proj['filament_colour']            = FILAMENT_COLOURS
proj['filament_type']              = FILAMENT_TYPES

# Clear preset inheritance so BambuStudio doesn't replace our settings
# with a newer version of the bundled preset
proj['inherits_group']             = ['', '', '', '', '', '']

# ── Print settings (Bambu Lab HueForge guide — X1C, Textured PEI) ─────────────
if NOZZLE == 0.2:
    FIRST_LAYER = '0.1'
    SPEEDS = dict(outer_wall='60', inner_wall='150', sparse_infill='100',
                  internal_solid_infill='150', top_surface='150', gap_infill='50')
    ACCELS = dict(default='4000', outer_wall='2000', top_surface='2000')
else:  # 0.4mm
    FIRST_LAYER = '0.24'
    SPEEDS = dict(outer_wall='200', inner_wall='200', sparse_infill='150',
                  internal_solid_infill='150', top_surface='150', gap_infill='200')
    ACCELS = dict(default='3000', outer_wall='1000', top_surface='1000')

proj['layer_height']               = LAYER_HEIGHT
proj['initial_layer_print_height'] = FIRST_LAYER
proj['curr_bed_type']              = 'High Temp Plate'

# Strength
proj['bottom_shell_layers']                 = '999'
proj['bottom_shell_thickness']              = '0'
proj['top_shell_layers']                    = '9'
proj['top_shell_thickness']                 = '0'
proj['sparse_infill_density']               = '100%'
proj['sparse_infill_pattern']               = 'grid'        # "grid" = Rectilinear in UI
proj['internal_solid_infill_pattern']       = 'grid'
proj['top_surface_pattern']                 = 'monotonic'
proj['bottom_surface_pattern']              = 'monotonic'
proj['detect_narrow_internal_solid_infill'] = '0'
proj['ensure_vertical_shell_thickness']     = 'disabled'

# Speed / acceleration — nozzle-dependent (set by NOZZLE above)
proj['outer_wall_speed']           = [SPEEDS['outer_wall']]
proj['inner_wall_speed']           = [SPEEDS['inner_wall']]
proj['sparse_infill_speed']        = [SPEEDS['sparse_infill']]
proj['internal_solid_infill_speed']= [SPEEDS['internal_solid_infill']]
proj['top_surface_speed']          = [SPEEDS['top_surface']]
proj['gap_infill_speed']           = [SPEEDS['gap_infill']]
proj['default_acceleration']       = [ACCELS['default']]
proj['outer_wall_acceleration']    = [ACCELS['outer_wall']]
proj['top_surface_acceleration']   = [ACCELS['top_surface']]

# Flush / prime tower
proj['flush_into_infill']          = '1'

TRUCK_PASSTHROUGH = [
    '[Content_Types].xml', '_rels/.rels', '3D/_rels/3dmodel.model.rels',
    'Metadata/plate_1.png', 'Metadata/plate_1_small.png',
    'Metadata/plate_no_light_1.png', 'Metadata/top_1.png',
    'Metadata/pick_1.png', 'Metadata/plate_1.json',
    'Metadata/cut_information.xml', 'Metadata/slice_info.config',
]

print(f"Writing {DST}...")
with zipfile.ZipFile(TRUCK_REF, 'r') as zt, \
     zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED) as zout:
    for name in TRUCK_PASSTHROUGH:
        if name in zt.namelist():
            zout.writestr(name, zt.read(name))
    zout.writestr('3D/Objects/object_1.model',           geom_xml)
    zout.writestr('3D/3dmodel.model',                    thin_3dmodel)
    zout.writestr('Metadata/custom_gcode_per_layer.xml', custom_gcode_xml)
    zout.writestr('Metadata/model_settings.config',      model_settings)
    zout.writestr('Metadata/project_settings.config',    json.dumps(proj, indent=2))

print(f"Done: {os.path.getsize(DST)/1024/1024:.1f} MB")
