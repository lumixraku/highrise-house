"""Export the generated The Stack scene as a web-ready binary glTF asset."""

import argparse
import os
import sys

import bpy


ROOT = os.path.dirname(os.path.abspath(__file__))


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

DEFAULT_SOURCE = os.path.join(ROOT, "out", "the_stack.blend")
DEFAULT_OUTPUT = os.path.join(ROOT, "web", "assets", "the_stack.glb")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=DEFAULT_SOURCE)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--no-merge-materials",
        action="store_true",
        help="Keep individual Blender mesh objects in the web export.",
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
    if not args.no_merge_materials:
        merge_meshes_by_material()
    bpy.ops.export_scene.gltf(
        filepath=output,
        export_format="GLB",
        export_apply=True,
        export_materials="EXPORT",
        export_cameras=False,
        export_lights=False,
    )
    print(f"Exported web asset: {output}")


if __name__ == "__main__":
    main()
