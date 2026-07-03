bl_info = {
    "name": "Edge Impulse Synthetic Data",
    "author": "Eoin Jordan",
    "version": (1, 0, 0),
    "blender": (3, 6, 0),
    "location": "View3D > Sidebar (N) > Edge Impulse",
    "description": "Generate labelled synthetic image datasets from a diorama and "
                   "upload them straight to Edge Impulse.",
    "category": "Render",
}

import bpy
import math
import os
import glob
import mimetypes
import uuid
import urllib.request
import urllib.error

from bpy.props import (
    StringProperty,
    IntProperty,
    FloatProperty,
    EnumProperty,
)
from bpy.types import (
    Operator,
    Panel,
    PropertyGroup,
)


INGESTION_URL = "https://ingestion.edgeimpulse.com/api/{category}/files"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _abspath(path):
    """Resolve Blender relative (//) and user (~) paths to an absolute path."""
    if not path:
        return ""
    return os.path.abspath(bpy.path.abspath(os.path.expanduser(path)))


def _report(op, level, message):
    op.report({level}, message)
    print(f"[Edge Impulse] {message}")


def _import_gltf(filepath):
    """Import a .glb/.gltf file and return the newly created objects."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=filepath)
    after = set(bpy.data.objects)
    return list(after - before)


def _build_multipart(files):
    """Build a multipart/form-data body from a list of (filename, bytes).

    Returns (body_bytes, content_type_header).
    """
    boundary = "----EdgeImpulseBoundary" + uuid.uuid4().hex
    crlf = b"\r\n"
    body = bytearray()

    for filename, content in files:
        mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        body += b"--" + boundary.encode() + crlf
        disposition = (
            f'Content-Disposition: form-data; name="data"; filename="{filename}"'
        )
        body += disposition.encode() + crlf
        body += f"Content-Type: {mime}".encode() + crlf + crlf
        body += content + crlf

    body += b"--" + boundary.encode() + b"--" + crlf
    content_type = f"multipart/form-data; boundary={boundary}"
    return bytes(body), content_type


def _upload_batch(api_key, category, label, files):
    """Upload a batch of files to the Edge Impulse ingestion API.

    files: list of (filename, bytes). Raises urllib errors on failure.
    """
    body, content_type = _build_multipart(files)
    url = INGESTION_URL.format(category=category)

    headers = {
        "x-api-key": api_key,
        "Content-Type": content_type,
    }
    if label:
        headers["x-label"] = label

    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.status, response.read().decode("utf-8", "replace")


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------
class EISyntheticProperties(PropertyGroup):
    diorama_path: StringProperty(
        name="Diorama",
        description="Path to the diorama .glb/.gltf file",
        subtype="FILE_PATH",
    )
    cars_folder: StringProperty(
        name="Assets Folder",
        description="Folder containing the object .glb/.gltf files to place in the scene",
        subtype="DIR_PATH",
    )
    output_folder: StringProperty(
        name="Output",
        description="Folder where rendered PNG frames are written",
        subtype="DIR_PATH",
        default="//images",
    )
    num_frames: IntProperty(
        name="Frames",
        description="Number of rotated frames to render",
        default=36,
        min=1,
        max=3600,
    )
    car_radius: FloatProperty(
        name="Radius",
        description="Radius of the circle the assets are placed on",
        default=3.0,
        min=0.0,
    )
    resolution_x: IntProperty(name="Res X", default=1920, min=16, max=8192)
    resolution_y: IntProperty(name="Res Y", default=1080, min=16, max=8192)
    render_engine: EnumProperty(
        name="Engine",
        items=[
            ("BLENDER_EEVEE", "EEVEE", "Fast rasterized renderer"),
            ("BLENDER_EEVEE_NEXT", "EEVEE Next", "Blender 4.2+ EEVEE"),
            ("CYCLES", "Cycles", "Physically based path tracer"),
        ],
        default="BLENDER_EEVEE",
    )
    api_key: StringProperty(
        name="API Key",
        description="Edge Impulse ingestion API key (ei_...)",
        subtype="PASSWORD",
    )
    label: StringProperty(
        name="Label",
        description="Label applied to every uploaded sample (e.g. 'car')",
        default="car",
    )
    category: EnumProperty(
        name="Category",
        items=[
            ("training", "Training", "Upload into the training set"),
            ("testing", "Testing", "Upload into the testing set"),
        ],
        default="training",
    )


# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------
class EI_OT_setup_scene(Operator):
    bl_idname = "ei.setup_scene"
    bl_label = "Setup Scene"
    bl_description = "Import the diorama and assets, place them, and add a camera and light"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.ei_synthetic
        diorama = _abspath(props.diorama_path)
        assets_folder = _abspath(props.cars_folder)

        if not os.path.isfile(diorama):
            _report(self, "ERROR", f"Diorama not found: {diorama}")
            return {"CANCELLED"}
        if not os.path.isdir(assets_folder):
            _report(self, "ERROR", f"Assets folder not found: {assets_folder}")
            return {"CANCELLED"}

        car_files = sorted(
            glob.glob(os.path.join(assets_folder, "*.glb"))
            + glob.glob(os.path.join(assets_folder, "*.gltf"))
        )
        if not car_files:
            _report(self, "ERROR", "No .glb/.gltf assets found in the assets folder")
            return {"CANCELLED"}

        # Import diorama.
        _import_gltf(diorama)

        # Import assets and collect their top-level objects.
        car_objects = []
        for car_file in car_files:
            imported = _import_gltf(car_file)
            car_objects.extend(o for o in imported if o.parent is None)

        # Rotation pivot at the origin.
        bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0))
        rotation_empty = context.active_object
        rotation_empty.name = "EI_RotationPivot"

        # Place assets in a circle and parent them to the pivot.
        count = max(len(car_objects), 1)
        for i, car_obj in enumerate(car_objects):
            angle = (2 * math.pi / count) * i
            car_obj.location = (
                props.car_radius * math.cos(angle),
                props.car_radius * math.sin(angle),
                0.0,
            )
            car_obj.parent = rotation_empty

        # Camera.
        bpy.ops.object.camera_add(
            location=(0, -8, 3), rotation=(math.radians(75), 0, 0)
        )
        context.scene.camera = context.active_object
        context.active_object.name = "EI_Camera"

        # Spot light.
        bpy.ops.object.light_add(
            type="SPOT", location=(0, -6, 6), rotation=(math.radians(75), 0, 0)
        )
        context.active_object.data.energy = 500
        context.active_object.name = "EI_Light"

        _report(self, "INFO", f"Scene ready with {len(car_objects)} asset(s)")
        return {"FINISHED"}


class EI_OT_render_dataset(Operator):
    bl_idname = "ei.render_dataset"
    bl_label = "Render Dataset"
    bl_description = "Rotate the scene and render the configured number of frames"
    bl_options = {"REGISTER"}

    def execute(self, context):
        props = context.scene.ei_synthetic
        output = _abspath(props.output_folder)
        os.makedirs(output, exist_ok=True)

        pivot = bpy.data.objects.get("EI_RotationPivot")
        if pivot is None:
            _report(self, "ERROR", "Run 'Setup Scene' first (no rotation pivot found)")
            return {"CANCELLED"}
        if context.scene.camera is None:
            _report(self, "ERROR", "No active camera in the scene")
            return {"CANCELLED"}

        scene = context.scene
        scene.render.image_settings.file_format = "PNG"
        scene.render.engine = props.render_engine
        scene.render.resolution_x = props.resolution_x
        scene.render.resolution_y = props.resolution_y

        for frame in range(props.num_frames):
            angle_deg = (360 / props.num_frames) * frame
            pivot.rotation_euler[2] = math.radians(angle_deg)
            context.view_layer.update()
            filename = f"{props.label}.render_{frame:03d}.png"
            scene.render.filepath = os.path.join(output, filename)
            bpy.ops.render.render(write_still=True)

        _report(self, "INFO", f"Rendered {props.num_frames} frame(s) to {output}")
        return {"FINISHED"}


class EI_OT_upload(Operator):
    bl_idname = "ei.upload"
    bl_label = "Upload to Edge Impulse"
    bl_description = "Upload the rendered PNG frames to your Edge Impulse project"
    bl_options = {"REGISTER"}

    def execute(self, context):
        props = context.scene.ei_synthetic
        output = _abspath(props.output_folder)

        if not props.api_key:
            _report(self, "ERROR", "Set your Edge Impulse API key first")
            return {"CANCELLED"}
        if not os.path.isdir(output):
            _report(self, "ERROR", f"Output folder not found: {output}")
            return {"CANCELLED"}

        images = sorted(glob.glob(os.path.join(output, "*.png")))
        if not images:
            _report(self, "ERROR", "No PNG images to upload. Render the dataset first")
            return {"CANCELLED"}

        uploaded = 0
        batch_size = 10  # keep requests small and reliable
        for start in range(0, len(images), batch_size):
            batch = images[start:start + batch_size]
            files = []
            for path in batch:
                with open(path, "rb") as handle:
                    files.append((os.path.basename(path), handle.read()))
            try:
                code, _ = _upload_batch(
                    props.api_key, props.category, props.label, files
                )
            except urllib.error.HTTPError as err:
                detail = err.read().decode("utf-8", "replace")
                _report(self, "ERROR", f"Upload failed ({err.code}): {detail}")
                return {"CANCELLED"}
            except urllib.error.URLError as err:
                _report(self, "ERROR", f"Network error: {err.reason}")
                return {"CANCELLED"}

            if code not in (200, 201):
                _report(self, "ERROR", f"Unexpected status {code} from ingestion API")
                return {"CANCELLED"}
            uploaded += len(batch)

        _report(self, "INFO", f"Uploaded {uploaded} image(s) to Edge Impulse")
        return {"FINISHED"}


class EI_OT_render_and_upload(Operator):
    bl_idname = "ei.render_and_upload"
    bl_label = "Render & Upload"
    bl_description = "Render the dataset and upload it to Edge Impulse in one step"
    bl_options = {"REGISTER"}

    def execute(self, context):
        if bpy.ops.ei.render_dataset() != {"FINISHED"}:
            return {"CANCELLED"}
        return bpy.ops.ei.upload()


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
class EI_PT_panel(Panel):
    bl_label = "Edge Impulse Synthetic Data"
    bl_idname = "EI_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Edge Impulse"

    def draw(self, context):
        layout = self.layout
        props = context.scene.ei_synthetic

        box = layout.box()
        box.label(text="Assets", icon="MESH_DATA")
        box.prop(props, "diorama_path")
        box.prop(props, "cars_folder")

        box = layout.box()
        box.label(text="Render", icon="RENDER_STILL")
        box.prop(props, "output_folder")
        box.prop(props, "render_engine")
        row = box.row(align=True)
        row.prop(props, "resolution_x")
        row.prop(props, "resolution_y")
        row = box.row(align=True)
        row.prop(props, "num_frames")
        row.prop(props, "car_radius")

        box = layout.box()
        box.label(text="Edge Impulse", icon="EXPORT")
        box.prop(props, "api_key")
        box.prop(props, "label")
        box.prop(props, "category")

        layout.separator()
        layout.operator("ei.setup_scene", icon="SCENE_DATA")
        layout.operator("ei.render_dataset", icon="RENDER_ANIMATION")
        layout.operator("ei.upload", icon="URL")
        layout.operator("ei.render_and_upload", icon="EXPORT")


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------
classes = (
    EISyntheticProperties,
    EI_OT_setup_scene,
    EI_OT_render_dataset,
    EI_OT_upload,
    EI_OT_render_and_upload,
    EI_PT_panel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.ei_synthetic = bpy.props.PointerProperty(type=EISyntheticProperties)


def unregister():
    del bpy.types.Scene.ei_synthetic
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
