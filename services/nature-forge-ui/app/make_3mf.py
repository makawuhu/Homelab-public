"""
make_3mf.py — Generate a BambuStudio-native 3MF from a nature-forge STL output.

Self-contained: no external truck reference required. All structural 3MF XML
and base BambuStudio settings are embedded.
"""
import json
import os
import zipfile

import trimesh


# ── Standard 3MF structural files ─────────────────────────────────────────────

_CONTENT_TYPES = """\
<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
  <Default Extension="png" ContentType="image/png"/>
  <Default Extension="json" ContentType="application/json"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Default Extension="config" ContentType="application/xml"/>
</Types>"""

_PACKAGE_RELS = """\
<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel" Target="/3D/3dmodel.model" Id="rel-1"/>
</Relationships>"""

_MODEL_RELS = """\
<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel" Target="/3D/Objects/object_1.model" Id="rel-1"/>
</Relationships>"""

# Minimal BambuStudio process settings — all HueForge-critical values baked in.
# generate_3mf() overwrites speed/accel/filament/shell keys on top of this base.
_BASE_SETTINGS = {
    "printer_settings_id": "Bambu Lab X1 Carbon 0.4 nozzle",  # overwritten by generate_3mf
    "print_settings_id":   "0.08mm Extra Fine @BBL X1C",
    "wall_loops":               "1",
    "enable_prime_tower":       "0",
    "reduce_infill_retraction": "1",
    "timelapse_type":           "0",
    "enable_support":           "0",
}

# Optional preview/metadata files to pass through from truck_ref when available.
_PASSTHROUGH_OPTIONAL = [
    'Metadata/plate_1.png', 'Metadata/plate_1_small.png',
    'Metadata/plate_no_light_1.png', 'Metadata/top_1.png',
    'Metadata/pick_1.png', 'Metadata/plate_1.json',
    'Metadata/cut_information.xml', 'Metadata/slice_info.config',
]


def generate_3mf(
    stl_path: str,
    dst: str,
    nozzle: float,
    layer_height: str,
    filament_colours: list,
    filament_types: list,
    color_changes: list,
    truck_ref: str = None,
    log_callback=None,
    simplify_faces: int = 0,
) -> None:
    """
    Generate a BambuStudio-native 3MF file from a nature-forge STL.

    Args:
        stl_path:         Path to the STL file
        dst:              Output path for the generated 3MF
        nozzle:           Nozzle diameter in mm (0.4 or 0.2)
        layer_height:     Layer height string e.g. '0.08'
        filament_colours: List of 4 hex color strings e.g. ['#1c1c1c', ...]
        filament_types:   List of 4 type strings e.g. ['PLA', ...]
        color_changes:    List of (top_z_mm, slot_1indexed, hex_color) tuples
        truck_ref:        Optional path to a BambuStudio 3MF for thumbnail passthrough
        log_callback:     Optional callable(str) for streaming progress
    """
    def log(msg):
        if log_callback:
            log_callback(msg)
        else:
            print(msg, flush=True)

    if nozzle == 0.2:
        first_layer = '0.16'
        speeds = dict(outer_wall='60',  inner_wall='150', sparse_infill='100',
                      internal_solid_infill='150', top_surface='150', gap_infill='50')
        accels = dict(default='4000', outer_wall='2000', top_surface='2000')
    else:  # 0.4mm
        first_layer = '0.16'
        speeds = dict(outer_wall='200', inner_wall='200', sparse_infill='150',
                      internal_solid_infill='150', top_surface='150', gap_infill='200')
        accels = dict(default='3000', outer_wall='1000', top_surface='1000')

    log("Loading STL...")
    mesh = trimesh.load(stl_path)
    log(f"  Faces: {len(mesh.faces)}, watertight: {mesh.is_watertight}")

    mesh.merge_vertices()
    mesh.update_faces(mesh.unique_faces())
    mesh.update_faces(mesh.nondegenerate_faces())

    if not mesh.is_watertight:
        log("  Repairing mesh...")
        trimesh.repair.fill_holes(mesh)
        log(f"  After repair: watertight: {mesh.is_watertight}")

    if simplify_faces and simplify_faces > 0 and len(mesh.faces) > simplify_faces:
        log(f"  Simplifying {len(mesh.faces):,} → {simplify_faces:,} faces...")
        mesh = mesh.simplify_quadric_decimation(face_count=simplify_faces)
        log(f"  Simplified to {len(mesh.faces):,} faces")

    # Center mesh at origin in X/Y so the 128,128 plate transform lands it correctly
    cx = (float(mesh.bounds[0][0]) + float(mesh.bounds[1][0])) / 2
    cy = (float(mesh.bounds[0][1]) + float(mesh.bounds[1][1])) / 2
    mesh.vertices[:, 0] -= cx
    mesh.vertices[:, 1] -= cy

    min_z      = float(mesh.bounds[0][2])
    face_count = len(mesh.faces)
    log(f"  Using {face_count:,} faces, min Z: {min_z:.4f}, centered at ({cx:.2f}, {cy:.2f})")

    log("Building geometry XML...")
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">',
        '  <resources>', '    <object id="1" type="model">', '      <mesh>', '        <vertices>',
    ]
    for v in mesh.vertices:
        lines.append(f'          <vertex x="{v[0]:.7f}" y="{v[1]:.7f}" z="{v[2]:.7f}"/>')
    lines.append('        </vertices>\n        <triangles>')
    for f in mesh.faces:
        lines.append(f'          <triangle v1="{f[0]}" v2="{f[1]}" v3="{f[2]}"/>')
    lines += ['        </triangles>', '      </mesh>', '    </object>', '  </resources>', '</model>']
    geom_xml = '\n'.join(lines)
    log(f"  {len(geom_xml)/1024/1024:.1f} MB")

    z = -min_z

    thin_3dmodel = f'''<?xml version="1.0" encoding="UTF-8"?>
<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p">
 <metadata name="Application">BambuStudio-02.05.00.66</metadata>
 <metadata name="BambuStudio:3mfVersion">1</metadata>
 <metadata name="CreationDate">2026-04-24</metadata>
 <metadata name="ModificationDate">2026-04-24</metadata>
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
    for top_z, extruder, color in color_changes:
        custom_gcode_xml += f'<layer top_z="{top_z}" type="2" extruder="{extruder}" color="{color}" extra="" gcode="tool_change"/>\n'
    custom_gcode_xml += '<mode value="MultiAsSingle"/>\n</plate>\n</custom_gcodes_per_layer>'

    model_settings = f'''<?xml version="1.0" encoding="UTF-8"?>
<config>
  <object id="2">
    <metadata key="name" value="nature_forge_model"/>
    <metadata key="extruder" value="1"/>
    <metadata face_count="{face_count}"/>
    <part id="1" subtype="normal_part">
      <metadata key="name" value="nature_forge_model"/>
      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>
      <metadata key="source_file" value="nature_forge_model.stl"/>
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

    # Start from truck_ref if available, otherwise use built-in base settings
    if truck_ref and os.path.exists(truck_ref):
        with zipfile.ZipFile(truck_ref) as zt:
            proj = json.loads(zt.read('Metadata/project_settings.config'))
        passthrough_src = truck_ref
    else:
        proj = dict(_BASE_SETTINGS)
        passthrough_src = None

    proj['filament_colour'] = filament_colours
    proj['filament_type']   = filament_types

    proj['inherits_group'] = ['0.08mm Extra Fine @BBL X1C', '', '', '', '', '']

    nozzle_str = f'{nozzle:g}'
    proj['printer_model']       = 'Bambu Lab X1 Carbon'
    proj['printer_settings_id'] = f'Bambu Lab X1 Carbon {nozzle_str} nozzle'
    proj['printer_variant']     = nozzle_str
    proj['printer_structure']   = 'corexy'
    proj['printer_technology']  = 'FFF'
    proj['print_compatible_printers'] = [f'Bambu Lab X1 Carbon {nozzle_str} nozzle']

    proj['filament_map_mode'] = 'Auto For Flush'

    proj['layer_height']               = layer_height
    proj['initial_layer_print_height'] = first_layer
    proj['curr_bed_type']              = 'High Temp Plate'

    proj['resolution']                           = '0.012'
    proj['bottom_shell_layers']                 = '999'
    proj['bottom_shell_thickness']              = '0'
    proj['top_shell_layers']                    = '7'
    proj['top_shell_thickness']                 = '0'
    proj['sparse_infill_density']               = '100%'
    proj['sparse_infill_pattern']               = 'zig-zag'
    proj['internal_solid_infill_pattern']       = 'zig-zag'
    proj['top_surface_pattern']                 = 'monotonicline'
    proj['bottom_surface_pattern']              = 'monotonic'
    proj['detect_narrow_internal_solid_infill'] = '0'
    proj['ensure_vertical_shell_thickness']     = 'disabled'
    proj['wall_loops']                          = '1'
    proj['enable_prime_tower']                  = '0'
    proj['reduce_infill_retraction']            = '1'
    proj['bottom_color_penetration_layers']     = '5'
    proj['timelapse_type']                      = '0'

    proj['outer_wall_speed']            = [speeds['outer_wall']]
    proj['inner_wall_speed']            = [speeds['inner_wall']]
    proj['sparse_infill_speed']         = [speeds['sparse_infill']]
    proj['internal_solid_infill_speed'] = [speeds['internal_solid_infill']]
    proj['top_surface_speed']           = [speeds['top_surface']]
    proj['gap_infill_speed']            = [speeds['gap_infill']]
    proj['initial_layer_speed']         = ['50']
    proj['initial_layer_infill_speed']  = ['105']
    proj['default_acceleration']        = [accels['default']]
    proj['outer_wall_acceleration']     = [accels['outer_wall']]
    proj['top_surface_acceleration']    = [accels['top_surface']]
    proj['initial_layer_acceleration']  = ['500']

    proj['flush_into_infill']   = '1'
    proj['flush_into_support']  = '1'
    proj['flush_multiplier']    = ['0.5']
    # Flush volume matrix (4×4, mm³ per filament pair) — required for flush-into-infill
    # to work without BambuStudio forcing a prime tower. Values from HueForge reference.
    proj['flush_volumes_matrix'] = ['0','421','627','632','123','0','389','382','135','123','0','208','192','212','331','0']
    proj['flush_volumes_vector'] = ['140','140','140','140','140','140','140','140']
    proj['filament_prime_volume'] = ['45','30','30','30']

    os.makedirs(os.path.dirname(dst) if os.path.dirname(dst) else '.', exist_ok=True)
    log(f"Writing {dst}...")
    with zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as zout:
        zout.writestr('[Content_Types].xml',         _CONTENT_TYPES)
        zout.writestr('_rels/.rels',                 _PACKAGE_RELS)
        zout.writestr('3D/_rels/3dmodel.model.rels', _MODEL_RELS)

        if passthrough_src:
            with zipfile.ZipFile(passthrough_src, 'r') as zt:
                for name in _PASSTHROUGH_OPTIONAL:
                    if name in zt.namelist():
                        zout.writestr(name, zt.read(name))

        zout.writestr('3D/Objects/object_1.model',           geom_xml)
        zout.writestr('3D/3dmodel.model',                    thin_3dmodel)
        zout.writestr('Metadata/custom_gcode_per_layer.xml', custom_gcode_xml)
        zout.writestr('Metadata/model_settings.config',      model_settings)
        zout.writestr('Metadata/project_settings.config',    json.dumps(proj, indent=2))

    size_mb = os.path.getsize(dst) / 1024 / 1024
    log(f"Done: {size_mb:.1f} MB")
