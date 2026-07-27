# Helios
## WIP
## A modular, DCC-agnostic asset inspection and visualization framework

Helios is an extensible desktop application for inspecting and visualizing digital assets from dcc pipelines.

The project is built around a format independent scene graph, a pluggable importer system, and a renderer abstraction layer. The goal is to keep asset processing, application logic, and rendering concerns separate, making it easier to support new formats, workflows, and rendering technologies over time.

Rather than being a simple asset viewer, Helios is designed as a foundation for building production oriented tools around digital content.

---

# Architecture

Helios separates asset loading, scene representation, application systems, and rendering into independent layers.

```
                    +----------------+
                    |  Asset Files   |
                    | USD, FBX, etc. |
                    +-------+--------+
                            |
                            v
                    +----------------+
                    |   Importers    |
                    +-------+--------+
                            |
                            v
                    +----------------+
                    |   SceneGraph   |
                    +-------+--------+
                            |
             +--------------+--------------+
             |                             |
             v                             v
    +----------------+           +----------------+
    | Application    |           | Scene Extractor|
    | Services/Tools |           +--------+-------+
    +----------------+                    |
                                          v
                                  +---------------+
                                  | Renderer API  |
                                  +-------+-------+
                                          |
                                          v
                                  +---------------+
                                  | GPU Backend   |
                                  | OpenGL/Vulkan |
                                  +---------------+
```

The `SceneGraph` acts as the central representation of asset data.

Importers are responsible for translating external formats into this representation, while the renderer and application systems operate on the internal model without depending on source file formats.

---

# Scene Graph

Helios uses a component based scene architecture.

Scene nodes can contain components such as:

- Transform data
- Mesh geometry
- Materials
- Skeleton metadata
- Transform overrides

The scene graph does not depend on any specific asset format. External APIs such as USD, FBX, or other format libraries are isolated inside their respective importers.

This keeps downstream systems focused on working with scene data rather than understanding how that data was created.

---

# Import System

Assets are loaded through a common importer interface.

Current support:

- USD

Importers are responsible for:

- Reading source files
- Resolving format specific data
- Creating scene nodes and components
- Providing animation data
- Reporting import diagnostics

New formats can be introduced by implementing the importer interface while keeping the rest of the application unchanged.

---

# Rendering Architecture

Rendering is separated from the scene representation through a backend interface.

Current backend:

- OpenGL Core Profile

The renderer is responsible for:

- Render orchestration
- Render passes
- Shader management
- GPU resource management
- Viewport rendering

The viewport and application layer do not issue graphics API calls directly.

---

# Render Pipeline

Rendering is organised through independent render passes.

Current passes include:

- Geometry rendering
- Grid rendering
- Selection highlighting

Each pass owns a specific responsibility and can be extended without modifying unrelated rendering code.

Future extensions include:

- Debug visualization
- Viewport overlays
- Additional shading passes
- Alternative rendering backends

---

