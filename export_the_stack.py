"""Export the generated The Stack scene as a web-ready binary glTF asset."""

import argparse
import json
import os
import sys

import bpy


ROOT = os.path.dirname(os.path.abspath(__file__))


def _input_value(bsdf, name, fallback):
    if bsdf is None:
        return fallback
    socket = bsdf.inputs.get(name)
    return socket.default_value if socket else fallback


def _is_glass_like(material):
    """Detect glass from shader structure, not a project-specific name."""
    if not material.use_nodes:
        return False
    nodes = material.node_tree.nodes
    node_types = {node.type for node in nodes}
    if "BSDF_GLASS" in node_types:
        return True
    has_transparent = "BSDF_TRANSPARENT" in node_types
    has_reflection = bool(node_types & {"BSDF_GLOSSY", "BSDF_ANISOTROPIC"})
    if has_transparent and (has_reflection or "MIX_SHADER" in node_types):
        return True

    principled = nodes.get("Principled BSDF")
    transmission = float(_input_value(principled, "Transmission Weight", 0.0))
    alpha = float(_input_value(principled, "Alpha", 1.0))
    roughness = float(_input_value(principled, "Roughness", 0.5))
    ior = float(_input_value(principled, "IOR", 1.5))
    return (
        transmission > 0.05
        and 1.25 <= ior <= 2.0
        and roughness < 0.35
    ) or (alpha < 0.98 and 1.25 <= ior <= 2.0 and roughness < 0.35)


def _make_web_glass(material):
    source_bsdf = material.node_tree.nodes.get("Principled BSDF")
    source_alpha = float(_input_value(source_bsdf, "Alpha", 1.0))
    source_transmission = float(
        _input_value(source_bsdf, "Transmission Weight", 0.0)
    )
    frosted = source_alpha < 0.98 and source_transmission < 0.1
    web_material = bpy.data.materials.new(f"{material.name}_Web")
    web_material.use_nodes = True
    nodes = web_material.node_tree.nodes
    links = web_material.node_tree.links
    nodes.clear()
    output = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    links.new(bsdf.outputs[0], output.inputs[0])

    base_color = _input_value(
        source_bsdf, "Base Color", tuple(material.diffuse_color)
    )
    bsdf.inputs["Base Color"].default_value = base_color
    bsdf.inputs["Metallic"].default_value = 0.0
    source_roughness = float(_input_value(source_bsdf, "Roughness", 0.03))
    bsdf.inputs["Roughness"].default_value = (
        source_roughness if frosted or source_transmission > 0.05 else 0.03
    )
    bsdf.inputs["IOR"].default_value = float(
        _input_value(source_bsdf, "IOR", 1.52)
    )
    if "Transmission Weight" in bsdf.inputs:
        bsdf.inputs["Transmission Weight"].default_value = (
            0.18 if frosted else max(source_transmission, 0.48)
        )
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 1.0
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = 0.25 if frosted else 0.6
    if "Coat Roughness" in bsdf.inputs:
        bsdf.inputs["Coat Roughness"].default_value = 0.03
    if "Alpha" in bsdf.inputs:
        bsdf.inputs["Alpha"].default_value = source_alpha if frosted else 1.0

    web_material.diffuse_color = base_color
    if frosted and hasattr(web_material, "surface_render_method"):
        web_material.surface_render_method = "DITHERED"
    return web_material


def translate_glass_materials():
    """Translate unsupported Blender glass nodes on the export copy only."""
    cache = {}
    translated = 0
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH":
            continue
        for index, material in enumerate(obj.data.materials):
            if not material or not _is_glass_like(material):
                continue
            if material.name not in cache:
                cache[material.name] = _make_web_glass(material)
                translated += 1
            obj.data.materials[index] = cache[material.name]
    print(f"Translated Blender glass materials for glTF: {translated}")
    return translated


def scene_report(profile, compression, output, translated_glass, merged):
    mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    vertices = sum(len(obj.data.vertices) for obj in mesh_objects)
    polygons = sum(len(obj.data.polygons) for obj in mesh_objects)
    triangles = sum(
        sum(max(0, len(poly.vertices) - 2) for poly in obj.data.polygons)
        for obj in mesh_objects
    )
    materials = sorted({
        material.name
        for obj in mesh_objects
        for material in obj.data.materials
        if material
    })
    return {
        "profile": profile,
        "compression": compression,
        "output": output,
        "file_bytes": os.path.getsize(output) if os.path.exists(output) else 0,
        "mesh_objects": len(mesh_objects),
        "vertices": vertices,
        "polygons": polygons,
        "triangles": triangles,
        "materials": len(materials),
        "translated_glass_materials": translated_glass,
        "merged_meshes": merged,
    }


def merge_meshes_by_material():
    """Merge web-export meshes without changing the source .blend on disk."""
    groups = {}
    for obj in bpy.context.scene.objects:
        if obj.type != "MESH" or len(obj.data.materials) != 1:
            continue
        material = obj.data.materials[0]
        groups.setdefault(material.name, []).append(obj)

    before = sum(len(objects) for objects in groups.values())
    for material_name, objects in groups.items():
        if len(objects) < 2:
            continue
        bpy.ops.object.select_all(action="DESELECT")
        for obj in objects:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = objects[0]
        bpy.ops.object.join()
        objects[0].name = f"Web_{material_name}"

    after = len([obj for obj in bpy.context.scene.objects if obj.type == "MESH"])
    print(f"Merged web meshes by material: {before} -> {after}")
    return {"before": before, "after": after}

DEFAULT_SOURCE = os.path.join(ROOT, "out", "the_stack.blend")
DEFAULT_OUTPUT = os.path.join(ROOT, "web", "assets", "the_stack.glb")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--profile",
        choices=("static", "animated", "architectural"),
        default="architectural",
        help="Export policy for the source scene.",
    )
    parser.add_argument(
        "--no-merge-materials",
        action="store_true",
        help="Keep individual Blender mesh objects in the web export.",
    )
    parser.add_argument(
        "--compression",
        choices=("meshopt", "draco", "none"),
        default="meshopt",
        help="Geometry compression used by the browser asset.",
    )
    parser.add_argument(
        "--preserve-materials",
        action="store_true",
        help="Do not translate unsupported Blender glass node graphs.",
    )
    parser.add_argument(
        "--report",
        nargs="?",
        const="-",
        help="Print the export report or write it to a JSON path.",
    )
    args = parser.parse_args(
        sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    )

    source = os.path.abspath(args.source)
    output = os.path.abspath(args.output)
    if not os.path.exists(source):
        raise FileNotFoundError(f"Blender scene not found: {source}")

    os.makedirs(os.path.dirname(output), exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=source)
    translated_glass = 0
    if not args.preserve_materials:
        translated_glass = translate_glass_materials()
    merged = {"before": len([obj for obj in bpy.context.scene.objects if obj.type == "MESH"]),
              "after": len([obj for obj in bpy.context.scene.objects if obj.type == "MESH"])}
    if args.profile != "animated" and not args.no_merge_materials:
        merged = merge_meshes_by_material()

    export_options = {
        "filepath": output,
        "export_format": "GLB",
        "export_apply": True,
        "export_materials": "EXPORT",
        "export_cameras": False,
        "export_lights": False,
    }
    if args.compression == "meshopt":
        export_options.update(
            export_meshopt_compression_enable=True,
            export_meshopt_extension="EXT_meshopt_compression",
        )
    elif args.compression == "draco":
        export_options.update(
            export_draco_mesh_compression_enable=True,
            export_draco_mesh_compression_level=6,
        )
    bpy.ops.export_scene.gltf(**export_options)
    report = scene_report(
        args.profile, args.compression, output, translated_glass, merged
    )
    if args.report:
        payload = json.dumps(report, indent=2, sort_keys=True)
        if args.report == "-":
            print(payload)
        else:
            with open(os.path.abspath(args.report), "w", encoding="utf-8") as file:
                file.write(payload + "\n")
            print(f"Wrote export report: {os.path.abspath(args.report)}")
    print(f"Exported web asset: {output}")


if __name__ == "__main__":
    main()
