"""Build an editable, stylized Centre Pompidou architectural scene."""

import math
import os
import sys

import bpy
from mathutils import Vector


OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
BLEND_PATH = os.path.join(OUT_DIR, "centre_pompidou.blend")
RENDER_PATH = os.path.join(OUT_DIR, "centre_pompidou_preview.png")
FRONT_RENDER_PATH = os.path.join(OUT_DIR, "centre_pompidou_front.png")
SIDE_RENDER_PATH = os.path.join(OUT_DIR, "centre_pompidou_side.png")

WIDTH = 216.0
DEPTH = 60.0
FLOORS = 7
FLOOR_H = 10.0
BUILDING_H = FLOORS * FLOOR_H
FRAME_X = WIDTH / 2 + 3.0
BALCONY_DEPTH = 4.0
BALCONY_FLOOR_OFFSET = 0.05
FRAME_CLEARANCE = 4.25
FRAME_Y = DEPTH / 2 + FRAME_CLEARANCE + 0.32
FRAME_Z = BUILDING_H + 3.0
BAYS = 17


def material(name, color, metallic=0.0, roughness=0.45, emission=None):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if emission:
        bsdf.inputs["Emission Color"].default_value = emission
        bsdf.inputs["Emission Strength"].default_value = 2.0
    return mat


def glass_material(name="Escalator_Glass", color=(0.45, 0.72, 0.86, 1.0), alpha=0.62):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color[:3], alpha)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = 0.02
    bsdf.inputs["Metallic"].default_value = 0.18
    bsdf.inputs["Transmission Weight"].default_value = 0.9
    bsdf.inputs["Alpha"].default_value = alpha
    mat.surface_render_method = "DITHERED"
    return mat


def cube(name, location, scale, mat, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = (scale[0] / 2, scale[1] / 2, scale[2] / 2)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new("Edge bevel", "BEVEL")
        mod.width = bevel
        mod.segments = 2
    return obj


def cylinder(name, location, radius, depth, mat, rotation=(0, 0, 0), vertices=16):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=vertices, radius=radius, depth=depth, location=location,
        rotation=rotation,
    )
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    return obj


def beam(name, start, end, radius, mat, vertices=10):
    start, end = Vector(start), Vector(end)
    delta = end - start
    obj = cylinder(name, (start + end) / 2, radius, delta.length, mat, vertices=vertices)
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = delta.to_track_quat("Z", "Y")
    return obj


def oriented_box(name, start, end, width, height, mat):
    """Create a rectangular member aligned to a line in the XZ plane."""
    start, end = Vector(start), Vector(end)
    delta = end - start
    obj = cube(name, (start + end) / 2, (delta.length, width, height), mat)
    obj.rotation_euler[1] = -math.atan2(delta.z, delta.x)
    return obj


def curve_tube(name, points, radius, mat, cyclic=False):
    curve = bpy.data.curves.new(name + "_Curve", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.bevel_depth = radius
    curve.bevel_resolution = 3
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for point, co in zip(spline.bezier_points, points):
        point.co = co
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"
    spline.use_cyclic_u = cyclic
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def add_structure(mats):
    bay = WIDTH / BAYS
    for side in (-1, 1):
        y = side * FRAME_Y
        for i in range(BAYS + 1):
            x = -WIDTH / 2 + i * bay
            beam("White_Frame_Column", (x, y, 0), (x, y, FRAME_Z), 0.32, mats["white"])
        for level in range(FLOORS + 1):
            z = level * FLOOR_H - 0.35
            beam("White_Frame_Horizontal", (-WIDTH / 2, y, z), (WIDTH / 2, y, z), 0.28, mats["white"])
        for i in range(BAYS):
            x0 = -WIDTH / 2 + i * bay
            x1 = x0 + bay
            for level in range(1, FLOORS):
                z0, z1 = level * FLOOR_H, (level + 1) * FLOOR_H
                if (i + level) % 2:
                    beam("White_Frame_Brace", (x0, y, z0), (x1, y, z1), 0.18, mats["white"])
                else:
                    beam("White_Frame_Brace", (x0, y, z1), (x1, y, z0), 0.18, mats["white"])
        for i in range(BAYS + 1):
            x = -WIDTH / 2 + i * bay
            beam("Gerberette", (x, side * DEPTH / 2, FRAME_Z - 2.0),
                 (x, y, FRAME_Z), 0.38, mats["white"])
            beam("Roof_Tie", (x, y, FRAME_Z), (x, side * 12.0, FRAME_Z + 5.0),
                 0.16, mats["white"])

    # The short elevations receive the same exposed diagonal language, using
    # their five facade bays to keep the cross-bracing legible at the ends.
    short_bay = DEPTH / 5
    for side in (-1, 1):
        x = side * FRAME_X
        for i in range(6):
            y = -DEPTH / 2 + i * short_bay
            beam("Short_Frame_Column", (x, y, 0), (x, y, FRAME_Z), 0.32, mats["white"])
        for level in range(FLOORS + 1):
            z = level * FLOOR_H - 0.35
            beam("Short_Frame_Horizontal", (x, -DEPTH / 2, z),
                 (x, DEPTH / 2, z), 0.28, mats["white"])
        for i in range(5):
            y0 = -DEPTH / 2 + i * short_bay
            y1 = y0 + short_bay
            for level in range(1, FLOORS):
                z0, z1 = level * FLOOR_H, (level + 1) * FLOOR_H
                if (i + level) % 2:
                    beam("Short_Frame_Brace", (x, y0, z0), (x, y1, z1), 0.18, mats["white"])
                else:
                    beam("Short_Frame_Brace", (x, y0, z1), (x, y1, z0), 0.18, mats["white"])


def add_building(mats):
    for level in range(FLOORS + 1):
        z = level * FLOOR_H
        cube("Floor_Slab", (0, 0, z), (WIDTH, DEPTH, 0.42), mats["concrete"])
    outer_width = WIDTH + 2 * BALCONY_DEPTH
    outer_depth = DEPTH + 2 * BALCONY_DEPTH
    for level in range(1, FLOORS + 1):
        z = level * FLOOR_H + BALCONY_FLOOR_OFFSET
        for side in (-1, 1):
            cube("Perimeter_Balcony_Slab", (0, side * (DEPTH / 2 + BALCONY_DEPTH / 2), z),
                 (outer_width, BALCONY_DEPTH, 0.32), mats["concrete"])
            cube("Perimeter_Balcony_Railing", (0, side * outer_depth / 2, z + 0.81),
                 (outer_width, 0.10, 1.30), mats["steel"])
            cube("Perimeter_Balcony_Slab", (side * (WIDTH / 2 + BALCONY_DEPTH / 2), 0, z),
                 (BALCONY_DEPTH, DEPTH, 0.32), mats["concrete"])
            cube("Perimeter_Balcony_Railing", (side * outer_width / 2, 0, z + 0.81),
                 (0.10, DEPTH, 1.30), mats["steel"])
    for side in (-1, 1):
        y = side * DEPTH / 2
        for level in range(1, FLOORS):
            z = level * FLOOR_H + FLOOR_H / 2
            for bay in range(BAYS):
                x = -WIDTH / 2 + (bay + 0.5) * WIDTH / BAYS
                cube("Curtain_Wall_Panel", (x, y, z),
                     (WIDTH / BAYS - 0.22, 0.075, FLOOR_H - 0.55),
                     mats["facade_glass"])
        for level in range(FLOORS + 1):
            cube("Curtain_Wall_Transom", (0, y + side * 0.08, level * FLOOR_H),
                 (WIDTH, 0.16, 0.11), mats["steel"])
    short_bays = 5
    for side in (-1, 1):
        x = side * WIDTH / 2
        for level in range(1, FLOORS):
            z = level * FLOOR_H + FLOOR_H / 2
            for bay in range(short_bays):
                y = -DEPTH / 2 + (bay + 0.5) * DEPTH / short_bays
                cube("Short_Facade_Glass_Panel", (x, y, z),
                     (0.075, DEPTH / short_bays - 0.22, FLOOR_H - 0.55),
                     mats["facade_glass"])
        for level in range(1, FLOORS + 1):
            cube("Short_Facade_Transom", (x + side * 0.08, 0, level * FLOOR_H),
                 (0.16, DEPTH, 0.11), mats["steel"])
    for level in range(1, FLOORS):
        z = level * FLOOR_H + FLOOR_H / 2
        for x in range(-55, 56, 10):
            cube("Interior_Light", (x, -DEPTH / 2 + 0.5, z),
                 (5.2, 0.3, 0.45), mats["light"])


def add_bim_detail(mats):
    """Add separable architectural, structural, MEP, and vertical-transport parts."""
    bay = WIDTH / BAYS

    # Keep the floor plates completely open. All primary vertical structure is
    # carried by the exposed perimeter frames; no internal columns or trusses
    # are added inside the glazed volume.

    # One explicit floor assembly per level: ceiling plenum, raised floor strips,
    # and a sparse service distribution rack.
    for level in range(FLOORS):
        z = level * FLOOR_H
        for x in range(-56, 57, 4):
            cube("Raised_Floor_Module", (x, 0, z + 0.7), (3.65, DEPTH - 8, 0.12), mats["concrete"])
        for x in range(-56, 57, 8):
            cube("Ceiling_Grid_Main", (x, 0, z + FLOOR_H - 0.65), (0.09, DEPTH - 8, 0.09), mats["steel"])
        for y in range(-22, 23, 5):
            cube("Ceiling_Grid_Cross", (0, y, z + FLOOR_H - 0.65), (WIDTH - 10, 0.07, 0.07), mats["steel"])
        for x in (-48, -32, -16, 0, 16, 32, 48):
            beam("MEP_Rack_Blue", (x, -23, z + 3.9), (x + bay * 0.65, -23, z + 3.9), 0.22, mats["blue"])
            beam("MEP_Rack_Green", (x, -21.8, z + 4.25), (x + bay * 0.65, -21.8, z + 4.25), 0.13, mats["green"])
            beam("MEP_Rack_Yellow", (x, -20.8, z + 4.6), (x + bay * 0.65, -20.8, z + 4.6), 0.11, mats["yellow"])

    # Service facade standoffs and repeating panel joints make the exposed skin
    # read as a coordinated BIM curtain-wall system rather than a flat plane.
    for side in (-1, 1):
        y = side * (DEPTH / 2 + 0.32)
        for level in range(FLOORS):
            z = level * FLOOR_H - 0.35
            for bay_index in range(BAYS):
                x = -WIDTH / 2 + (bay_index + 0.5) * bay
                beam("Facade_Panel_Standoff", (x, y, z), (x, side * FRAME_Y, z), 0.11, mats["steel"])
                cube("Facade_Sill_Flash", (x, y, z), (bay - 0.15, 0.20, 0.10), mats["steel"])

def add_services(mats):
    pipe_specs = [
        ("Blue_Air_Duct", -50, 2.0, mats["blue"]),
        ("Green_Water_Pipe", -43, 0.9, mats["green"]),
        ("Yellow_Electrical", 46, 0.8, mats["yellow"]),
        ("Red_Circulation", 54, 1.15, mats["red"]),
    ]
    for side in (-1, 1):
        y = side * (FRAME_Y + 0.8)
        for name, x, radius, mat in pipe_specs:
            cylinder(name, (x, y, BUILDING_H / 2), radius, BUILDING_H + 7, mat)
            curve_tube(name + "_Roof_Bend", [
                (x, y, BUILDING_H + 3.5),
                (x, y, BUILDING_H + 7.0),
                (x + (-6 if x < 0 else 6), y, BUILDING_H + 8.5),
            ], radius, mat)
        for level in range(FLOORS):
            z = level * FLOOR_H + 1.7
            for x in range(-56, 57, 16):
                cylinder("Blue_Service_Duct", (x, y + side * 0.4, z), 0.55, 5.8,
                         mats["blue"], rotation=(math.pi / 2, 0, 0), vertices=14)
                cylinder("Green_Service_Pipe", (x + 4, y + side * 0.6, z + 1.2), 0.24, 5.5,
                         mats["green"], rotation=(math.pi / 2, 0, 0), vertices=12)


def add_escalator(mats):
    landing_x = [-90.0 + level * 30.0 for level in range(7)]
    landing_length = 12.0
    tube_radius = 2.75
    tube_z = 1.65

    def route(prefix, y, route_x):
        enclosure_path = []
        for level, x in enumerate(route_x):
            z = level * FLOOR_H + tube_z
            enclosure_path.extend([
                (x - landing_length / 2, y, z),
                (x + landing_length / 2, y, z),
            ] if route_x[-1] > route_x[0] else [
                (x + landing_length / 2, y, z),
                (x - landing_length / 2, y, z),
            ])
        curve_tube(prefix + "_Continuous_Glass_Tube", enclosure_path,
                   tube_radius, mats["tube"])

        for level, x in enumerate(route_x):
            z = level * FLOOR_H
            cube(prefix + "_Horizontal_Landing", (x, y, z + 0.25),
                 (landing_length, 5.2, 0.5), mats["white"], 0.16)
            landing_rib_count = math.ceil(landing_length / 2.0)
            for rib_index in range(landing_rib_count + 1):
                frame_x = x - landing_length / 2 + landing_length * rib_index / landing_rib_count
                bpy.ops.mesh.primitive_torus_add(
                    major_radius=tube_radius + 0.01, minor_radius=0.12,
                    major_segments=32, minor_segments=8,
                    location=(frame_x, y, z + 1.65), rotation=(0, math.pi / 2, 0),
                )
                rib = bpy.context.object
                rib.name = prefix + "_Landing_Rib"
                rib.data.materials.append(mats["white"])

        for level in range(6):
            if route_x[-1] > route_x[0]:
                start_x = route_x[level] + landing_length / 2 - 0.25
                end_x = route_x[level + 1] - landing_length / 2 + 0.25
            else:
                start_x = route_x[level] - landing_length / 2 + 0.25
                end_x = route_x[level + 1] + landing_length / 2 - 0.25
            start = (start_x, y, level * FLOOR_H + 0.25)
            end = (end_x, y, (level + 1) * FLOOR_H + 0.25)
            flight = oriented_box(prefix + "_Flight", start, end, 2.2, 0.42,
                                  mats["escalator"])
            flight["route_direction"] = 1 if end_x > start_x else -1
            flight["slope_degrees"] = math.degrees(
                math.atan2(end[2] - start[2], abs(end_x - start_x))
            )
            for step in range(35):
                t = step / 34
                x = start[0] + (end[0] - start[0]) * t
                z = start[2] + (end[2] - start[2]) * t
                cube(prefix + "_Tread", (x, y - 0.02, z + 0.24),
                     (0.42, 2.05, 0.16), mats["metal"])
            for side in (-1, 1):
                rail_y = y + side * 1.3
                oriented_box(prefix + "_Glass_Balustrade", start, end,
                             0.08, 1.35, mats["tube"])
                bpy.context.object.location.y = rail_y
                beam(prefix + "_Red_Handrail",
                     (start[0], rail_y, start[2] + 1.15),
                     (end[0], rail_y, end[2] + 1.15),
                     0.11, mats["red"], vertices=12)

            enclosure_start = Vector(enclosure_path[level * 2 + 1])
            enclosure_end = Vector(enclosure_path[level * 2 + 2])
            delta = enclosure_end - enclosure_start
            rib_count = math.ceil(delta.length / 2.0)
            for frame_index in range(1, rib_count):
                center = enclosure_start.lerp(enclosure_end, frame_index / rib_count)
                bpy.ops.mesh.primitive_torus_add(
                    major_radius=tube_radius + 0.01, minor_radius=0.12,
                    major_segments=32, minor_segments=8, location=center,
                )
                rib = bpy.context.object
                rib.name = prefix + "_Enclosure_Rib"
                rib.rotation_mode = "QUATERNION"
                rib.rotation_quaternion = delta.to_track_quat("Z", "Y")
                rib.data.materials.append(mats["white"])

    route("Escalator_Left_Facade_Up", -(FRAME_Y + 5.0), landing_x)
    route("Escalator_Right_Facade_Up", FRAME_Y + 5.0, list(reversed(landing_x)))


def add_site(mats):
    cube("Pompidou_Plaza", (0, -22, -0.8), (WIDTH + 24.0, 115, 1.4), mats["plaza"], 0.25)
    for i in range(9):
        y = -78 + i * 7.5
        cube("Plaza_Step", (0, y, -0.02 + i * 0.08),
             (WIDTH + 19.0, 0.35, 0.18), mats["concrete"])
    cube("Roof_Service_Block", (28, 6, BUILDING_H + 2.8),
         (20, 13, 5.2), mats["dark"], 0.5)
    for x in (-38, -22, 5, 42):
        cylinder("Roof_Vent", (x, 4, BUILDING_H + 3.4), 1.3, 6.5, mats["blue"])


def setup_world_and_camera():
    if bpy.context.scene.world is None:
        bpy.context.scene.world = bpy.data.worlds.new("Pompidou_World")
    world = bpy.context.scene.world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.14, 0.20, 0.27, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.7

    bpy.ops.object.light_add(type="SUN", location=(0, 0, 90))
    sun = bpy.context.object
    sun.name = "Sun_Light"
    sun.data.energy = 2.2
    sun.data.angle = math.radians(18)
    sun.rotation_euler = (math.radians(28), math.radians(-18), math.radians(-35))

    bpy.ops.object.light_add(type="AREA", location=(-55, -85, 90))
    key = bpy.context.object
    key.name = "Key_Light"
    key.data.energy = 7000
    key.data.shape = "DISK"
    key.data.size = 65
    key.rotation_euler = (math.radians(28), 0, math.radians(-22))

    bpy.ops.object.light_add(type="AREA", location=(80, 35, 55))
    fill = bpy.context.object
    fill.name = "Fill_Light"
    fill.data.energy = 5000
    fill.data.size = 55
    fill.rotation_euler = (math.radians(65), 0, math.radians(135))

    bpy.ops.object.camera_add(location=(195, -225, BUILDING_H + 68.0))
    camera = bpy.context.object
    camera.name = "Pompidou_Camera"
    direction = Vector((0, -5, BUILDING_H / 2)) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    camera.data.lens = 55
    bpy.context.scene.camera = camera

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1400
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = RENDER_PATH
    scene.render.film_transparent = False
    scene.render.image_settings.color_mode = "RGBA"
    scene.view_settings.look = "AgX - Medium High Contrast"


def render_front_elevation(scene, camera):
    camera.location = (0, -240, BUILDING_H / 2)
    camera.rotation_euler = (math.pi / 2, 0, 0)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = max(
        WIDTH + 20.0,
        (BUILDING_H + 12.0) * scene.render.resolution_x / scene.render.resolution_y,
    )
    scene.render.resolution_x = 1660
    scene.render.resolution_y = 620
    scene.render.filepath = FRONT_RENDER_PATH
    bpy.ops.render.render(write_still=True)


def render_side_elevation(scene, camera):
    camera.location = (WIDTH / 2 + 180.0, 0, BUILDING_H / 2)
    camera.rotation_euler = (math.pi / 2, 0, math.pi / 2)
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = BUILDING_H + 18.0
    scene.render.resolution_x = 920
    scene.render.resolution_y = 920
    scene.render.filepath = SIDE_RENDER_PATH
    bpy.ops.render.render(write_still=True)


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    os.makedirs(OUT_DIR, exist_ok=True)
    mats = {
        "white": material("Structure_White", (0.82, 0.85, 0.85, 1), 0.55, 0.24),
        "dark": material("Interior_Dark", (0.025, 0.04, 0.055, 1), 0.35, 0.55),
        "concrete": material("Concrete", (0.32, 0.34, 0.34, 1), 0.0, 0.78),
        "plaza": material("Plaza_Stone", (0.25, 0.27, 0.27, 1), 0.0, 0.82),
        "steel": material("Facade_Steel", (0.58, 0.64, 0.67, 1), 0.7, 0.2),
        "facade_glass": glass_material("Facade_Glass", (0.07, 0.34, 0.50, 1.0), 0.68),
        "tube": glass_material("Escalator_Glass", (0.45, 0.72, 0.86, 1.0), 0.42),
        "escalator": material("Escalator_Belt", (0.10, 0.12, 0.14, 1), 0.3, 0.35),
        "metal": material("Escalator_Tread_Metal", (0.36, 0.40, 0.42, 1), 0.8, 0.22),
        "blue": material("Air_Blue", (0.015, 0.27, 0.72, 1), 0.38, 0.25),
        "green": material("Water_Green", (0.02, 0.48, 0.16, 1), 0.3, 0.25),
        "yellow": material("Electrical_Yellow", (1.0, 0.62, 0.01, 1), 0.25, 0.3),
        "red": material("Circulation_Red", (0.82, 0.025, 0.02, 1), 0.4, 0.25),
        "light": material("Interior_Light", (1.0, 0.65, 0.26, 1), 0.0, 0.25,
                          (1.0, 0.4, 0.08, 1)),
    }
    add_site(mats)
    add_building(mats)
    add_bim_detail(mats)
    add_structure(mats)
    add_services(mats)
    add_escalator(mats)
    setup_world_and_camera()
    bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
    if "--no-render" not in sys.argv:
        bpy.ops.render.render(write_still=True)
        render_front_elevation(bpy.context.scene, bpy.context.scene.camera)
        render_side_elevation(bpy.context.scene, bpy.context.scene.camera)
        bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH)
    print(f"Saved {BLEND_PATH}")
    print(f"Rendered {RENDER_PATH}")
    print(f"Rendered {FRONT_RENDER_PATH}")
    print(f"Rendered {SIDE_RENDER_PATH}")


if __name__ == "__main__":
    build()
