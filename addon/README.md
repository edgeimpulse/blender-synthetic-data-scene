# Edge Impulse Synthetic Data — Blender Add-on

A follow-up to the [Blender Synthetic Data Scene](../README.md) project. Instead of
pasting a script into the Scripting workspace, this packages the whole workflow into a
proper Blender **add-on** with a UI panel: import assets, render a rotated dataset, and
upload it straight to [Edge Impulse](https://studio.edgeimpulse.com/) — without leaving
Blender.

![diorama](https://github.com/user-attachments/assets/e6abb44a-6038-4f67-9716-603aa009f3d0)

## What it does

- Adds an **Edge Impulse** tab to the 3D Viewport sidebar (press `N`).
- Imports a diorama plus a folder of `.glb`/`.gltf` assets.
- Places assets in a circle, parents them to a rotation pivot, and adds a camera + light.
- Renders *n* rotated frames as labelled PNGs.
- Uploads the frames to your Edge Impulse project via the [Ingestion API](https://docs.edgeimpulse.com/reference/ingestion-api) — using only Python's standard library (no `pip install`).

## Install

1. Download `edge_impulse_synthetic.py`.
2. In Blender: **Edit → Preferences → Add-ons → Install…**
3. Select the file, then tick **Edge Impulse Synthetic Data** to enable it.
4. Open the 3D Viewport sidebar with `N` and select the **Edge Impulse** tab.

## Use

| Field | Meaning |
| --- | --- |
| **Diorama** | The `.glb`/`.gltf` backdrop file |
| **Assets Folder** | Folder of object models to place in the scene |
| **Output** | Where rendered PNGs are written (`//images` = next to the .blend) |
| **Engine / Res / Frames / Radius** | Render settings |
| **API Key** | Your Edge Impulse ingestion key (`ei_...`) |
| **Label** | Label applied to every sample |
| **Category** | Training or testing set |

Then click, in order:

1. **Setup Scene** — imports and arranges everything.
2. **Render Dataset** — renders the rotated frames.
3. **Upload to Edge Impulse** — pushes the PNGs to your project.

Or use **Render & Upload** to do the last two in one step.

## Where to find your API key

Edge Impulse Studio → your project → **Dashboard → Keys → Add new API key** (or use the
default key). Paste it into the **API Key** field. The key is stored as a password field
and sent only to `ingestion.edgeimpulse.com`.

## How the upload works

Blender ships its own Python, so the add-on avoids third-party dependencies. It builds a
`multipart/form-data` request by hand and posts batches of images to:

```
POST https://ingestion.edgeimpulse.com/api/training/files
x-api-key: ei_...
x-label: car
```

Each PNG lands in your project's Data acquisition tab, already labelled and ready for a
model.

## License

See [LICENSE](../LICENSE).
