Generate large, labelled image datasets from a 2D diorama using **Blender**, **Hunyuan 3D 2.0**, and **Edge Impulse**.



[Edge Impulse](https://studio.edgeimpulse.com/) · [Hunyuan 3D 2.0](https://github.com/Tencent/Hunyuan3D) · [Blender LTS](https://www.blender.org/download/)




## Project Overview

![diorama](https://github.com/user-attachments/assets/e6abb44a-6038-4f67-9716-603aa009f3d0)

- **Reusable Blender scene** with a parametric camera rig  
- **Python script** to:
  - Import 3D assets (diorama + cars)  
  - Scale and place assets in the scene  
  - Rotate the scene and render *n* images for training



## Quick Start

### Prepare 3D models with the latest demo version of [Hunyuan 3D 2.0](https://github.com/Tencent/Hunyuan3D) for free

![2dto3d](https://github.com/user-attachments/assets/05f4bad6-3c37-4f50-8c07-fe92cf8d4c61)


first you will need to grab some images of cars and a diorama, here are some samples I used:

![sample-car](https://github.com/user-attachments/assets/1be31127-6d88-4412-9780-a641eaf52a72)

![sample-diorama](https://github.com/user-attachments/assets/a2df94ea-de39-4b3b-97d2-5e24db5de64b)

Now update the following section of our python script to your generated assets and paths

```python
diorama_path = r"/Users/yourname/Downloads/your_diorama.glb"
car_paths = [
    r"/Users/yourname/Downloads/car1.glb",
    r"/Users/yourname/Downloads/car2.glb",
    # ...
]
output_folder = r"/Users/yourname/Downloads/images"
```

### Run the script in Blender
1. Open Blender

2. Switch to the Scripting workspace

3. Paste the contents from render_diorama.py

4. Click Run Script

The script will:

* Load the diorama and car models

* Position cars in a circle

* Set up lighting and camera

* Render 36 PNG images into output_folder

### Upload to Edge Impulse
Use any method of your own choosing to upload to Edge Impulse by following out [Data Aquistion Docs](https://docs.edgeimpulse.com/docs/edge-impulse-studio/data-acquisition)
