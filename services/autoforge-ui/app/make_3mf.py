"""
make_3mf.py — Generate a BambuStudio-native 3MF from an AutoForge STL output.

Canonical version — used by the autoforge-ui service.
docs/make_3mf.py is the manual/vast.ai version (kept for reference).
"""
import trimesh, zipfile, json, os


def generate_3mf(
    stl_path: str,
    truck_ref: str,
    dst: str,
    nozzle: float,
    layer_height: str,
    filament_colours: list,
    filament_types: list,
    color_changes: list,
    log_callback=None,
) -> None:
    """
    Generate a BambuStudio-native 3MF file.

    Args:
        stl_path: Path to the AutoForge STL output
        truck_ref: Path to a real BambuStudio 3MF used as structural template
        dst: Output path for the generated 3MF
        nozzle: Nozzle diameter in mm (0.4 or 0.2)
        layer_height: Layer height string e.g. '0.08'
        filament_colours: List of 4 hex color strings e.g. ['#1c1c1c', ...]
        filament_types: List of 4 type strings e.g. ['PLA', ...]
        color_changes: List of (top_z_mm, slot_1indexed, hex_color) tuples
        log_callback: Optional callable(str) for streaming progress
    """
    def log(msg):
        if log_callback:
            log_callback(msg)
        else:
            print(msg, flush=True)

    if nozzle == 0.2:
        first_layer = '0.1'
        speeds = dict(outer_wall='60', inner_wall='150', sparse_infill='100',
                      internal_solid_infill='150', top_surface='150', gap_infill='50')
        accels = dict(default='4000', outer_wall='2000', top_surface='2000')
    else:  # 0.4mm
        first_layer = '0.24'
        speeds = dict(outer_wall='200', inner_wall='200', sparse_infill='150',
                      internal_solid_infill='150', top_surface='150', gap_infill='200')
        accels = dict(default='3000', outer_wall='1000', top_surface='1000')

    log("Loading STL...")
    mesh = trimesh.load(stl_path)
    log(f"  Faces: {len(mesh.faces)}, watertight: {mesh.is_watertight}")

    # Always consolidate — ensures no near-duplicate vertices that Mac BambuStudio
    # may collapse differently, causing false non-manifold reports.
    mesh.merge_vertices()
    mesh.update_faces(mesh.unique_faces())
    mesh.update_faces(mesh.nondegenerate_faces())

    if not mesh.is_watertight:
        log("  Repairing mesh...")
        trimesh.repair.fill_holes(mesh)
        log(f"  After repair: watertight: {mesh.is_watertight}")

    min_z      = float(mesh.bounds[0][2])
    face_count = len(mesh.faces)
    log(f"  Using {face_count} faces, min Z: {min_z:.4f}")

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
    for top_z, extruder, color in color_changes:
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

    with zipfile.ZipFile(truck_ref) as zt:
        proj = json.loads(zt.read('Metadata/project_settings.config'))

    proj['filament_colour'] = filament_colours
    proj['filament_type']   = filament_types

    proj['inherits_group'] = ['', '', '', '', '', '']

    proj['layer_height']               = layer_height
    proj['initial_layer_print_height'] = first_layer
    proj['curr_bed_type']              = 'High Temp Plate'

    proj['bottom_shell_layers']                 = '999'
    proj['bottom_shell_thickness']              = '0'
    proj['top_shell_layers']                    = '9'
    proj['top_shell_thickness']                 = '0'
    proj['sparse_infill_density']               = '100%'
    proj['sparse_infill_pattern']               = 'zig-zag'
    proj['internal_solid_infill_pattern']       = 'zig-zag'
    proj['top_surface_pattern']                 = 'monotonic'
    proj['bottom_surface_pattern']              = 'monotonic'
    proj['detect_narrow_internal_solid_infill'] = '0'
    proj['ensure_vertical_shell_thickness']     = 'disabled'

    proj['outer_wall_speed']            = [speeds['outer_wall']]
    proj['inner_wall_speed']            = [speeds['inner_wall']]
    proj['sparse_infill_speed']         = [speeds['sparse_infill']]
    proj['internal_solid_infill_speed'] = [speeds['internal_solid_infill']]
    proj['top_surface_speed']           = [speeds['top_surface']]
    proj['gap_infill_speed']            = [speeds['gap_infill']]
    proj['default_acceleration']        = [accels['default']]
    proj['outer_wall_acceleration']     = [accels['outer_wall']]
    proj['top_surface_acceleration']    = [accels['top_surface']]

    proj['flush_into_infill'] = '1'

    PASSTHROUGH = [
        '[Content_Types].xml', '_rels/.rels', '3D/_rels/3dmodel.model.rels',
        'Metadata/plate_1.png', 'Metadata/plate_1_small.png',
        'Metadata/plate_no_light_1.png', 'Metadata/top_1.png',
        'Metadata/pick_1.png', 'Metadata/plate_1.json',
        'Metadata/cut_information.xml', 'Metadata/slice_info.config',
    ]

    os.makedirs(os.path.dirname(dst), exist_ok=True)
    log(f"Writing {dst}...")
    with zipfile.ZipFile(truck_ref, 'r') as zt, \
         zipfile.ZipFile(dst, 'w', zipfile.ZIP_DEFLATED) as zout:
        for name in PASSTHROUGH:
            if name in zt.namelist():
                zout.writestr(name, zt.read(name))
        zout.writestr('3D/Objects/object_1.model',           geom_xml)
        zout.writestr('3D/3dmodel.model',                    thin_3dmodel)
        zout.writestr('Metadata/custom_gcode_per_layer.xml', custom_gcode_xml)
        zout.writestr('Metadata/model_settings.config',      model_settings)
        zout.writestr('Metadata/project_settings.config',    json.dumps(proj, indent=2))

    size_mb = os.path.getsize(dst) / 1024 / 1024
    log(f"Done: {size_mb:.1f} MB")
