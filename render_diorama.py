import bpy
import math
import mathutils
import os

# --- USER SETTINGS ---
diorama_path = r"~/blender-synthetic-data-scene/your_diorama.glb"
car_paths = [
    r"~/blender-synthetic-data-scene/car1.glb",
    r"~/blender-synthetic-data-scene/car2.glb",
    r"~/blender-synthetic-data-scene/car3.glb",
    r"~/blender-synthetic-data-scene/car4.glb",
    r"~/blender-synthetic-data-scene/car5.glb"
]
output_folder = r"~/blender-synthetic-data-scene/images"

num_cars = len(car_paths)
car_radius = 3.0
car_bottom_z = 0.0
num_frames = 36

# --- IMPORT MODULES ---
import bpy
import math
import os

# --- CLEAR SCENE ---
#bpy.ops.object.select_all(action='SELECT')
#bpy.ops.object.delete(use_global=False)

# --- IMPORT DIORAMA ---
bpy.ops.import_scene.gltf(filepath=diorama_path)

# --- IMPORT CARS AND STORE OBJECTS ---
car_objects = []
for car_path in car_paths:
    bpy.ops.import_scene.gltf(filepath=car_path)
    for obj in bpy.context.selected_objects:
        car_objects = bpy.context.selected_objects

# --- POSITION CARS IN A CIRCLE ---
for i, car_obj in enumerate(car_objects):
    angle = (2 * math.pi / num_frames) * i
    x = car_radius * math.cos(angle)
    y = car_radius * math.sin(angle)
    car_obj.location = (x, y, car_bottom_z)

# --- IMPORT DIORAMA ---
bpy.ops.import_scene.gltf(filepath=diorama_path)

# --- CAMERA SETUP ---
bpy.ops.object.camera_add(location=(0, -8, 3), rotation=(math.radians(75), 0, 0))
bpy.context.scene.camera = bpy.context.active_object

# --- LIGHTING SETUP ---
bpy.ops.object.light_add(type='SPOT', location=(0, -6, 6), rotation=(math.radians(75), 0, 0))
spot_light = bpy.context.active_object
spot_light.data.energy = 500

# --- RENDER SETTINGS ---
bpy.context.scene.render.image_settings.file_format = 'PNG'
bpy.context.scene.render.engine = 'BLENDER_EEVEE'
bpy.context.scene.render.resolution_x = 1920
bpy.context.scene.render.resolution_y = 1080

# --- EMPTY FOR ROTATION ---
bpy.ops.object.empty_add(type='PLAIN_AXES', location=(0, 0, 0))
rotation_empty = bpy.context.active_object

# Parent cars to empty for easy rotation
for car_obj in car_objects:
    car_obj.parent = rotation_empty

# --- ROTATE & RENDER FRAMES ---
for frame in range(num_frames):
    angle_deg = (360 / num_frames) * frame
    rotation_empty.rotation_euler[2] = math.radians(angle_deg)
    bpy.context.view_layer.update()
    filename = f"render_{frame:03d}.png"
    bpy.context.scene.render.filepath = os.path.join("//", output_folder, filename)
    bpy.ops.render.render(write_still=True)

print("Rendering complete!")
