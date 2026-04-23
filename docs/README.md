# URDF Collision Editor

A professional Python desktop application for creating and editing URDF collision geometries for STL mesh files. Approximates complex meshes with primitive shapes (Box, Cylinder, Sphere) and exports URDF snippets.

---

## 🚀 Key Features
- **Multi-STL Management**: Load and navigate through multiple STL files in one session.
- **Interactive 3D View**: Real-time visualization of meshes and collision geometry using PyVista.
- **Support for STL Collisions**: Automatically import STL-based collision meshes from URDF. Edit their path, scale, and transform just like primitives.
- **Precision Editing**: Fine-grained control over position (metres) and orientation (degrees).
- **Normalized Scaling System**: Work in a clean "normalized" editor at scale 1.0. The tool automatically handles URDF visual scaling internally during export.
- **Undo/Redo System**: Full history support for all shape modifications.
- **URDF Export**: Generates XML collision snippets.
- **URDF Collision Injection**: Automatically injects collision primitives and STL meshes into an existing URDF file, matching links by mesh path and respecting original visual scales.
- **Smart Mesh Auto-Import**: Select a URDF and the program automatically loads all associated visual and collision STL meshes. Includes smart path resolution for ROS `package://` protocols.
- **Integrated Collision Validation**: Real-time feedback in the robot viewer. Collision shapes are color-coded (Green/Red) based on whether they intersect with other links in the robot assembly.
- **Robot Assembly Viewer**: A dedicated viewport showing the full assembled robot based on its URDF kinematics, allowing for multi-layer visualization (Visual Meshes and Collision Shapes).
- **Full Project Persistence**: Saves and loads the entire workspace (STLs, shapes, transforms, and linked URDF) to JSON.

---

## 🏛 Architecture (MVC Pattern)

The project follows a clean Model-View-Controller architecture for scalability and maintainability.

### 1. Model Layer (`models/`)
- **`ProjectState`**: The central state manager. Stores loaded meshes, navigation index, and the undo/redo stack.
- **`MeshModel`**: Represents a single STL file and its associated collection of collision shapes.
- **Shapes (`models/shapes/`)**: 
    - `BaseShape`: Abstract base defining spatial properties and URDF serialization logic.
    - `BoxShape`, `CylinderShape`, `SphereShape`, `StlShape`: Concrete geometry implementations.

### 2. Controller Layer (`controllers/`)
- **`FileController`**: Handles STL loading, navigation logic, and file-system interactions.
- **`ShapeController`**: Manages the lifecycle of collision shapes (add, update, delete) with undo/redo support.
- **`ExportController`**: Logic for generating URDF XML and serializing/deserializing JSON project files.

### 3. View Layer (`views/` & `visualization/`)
- **`MainWindow`**: The main UI shell connecting all components.
- **`FilePanel`**: Sidebar for file navigation.
- **`ShapeListPanel`**: Management panel for shapes associated with the active mesh.
- **`PropertyPanel`**: Dynamic form for editing shape dimensions and transforms.
- **`SceneManager`**: Dedicated 3D abstraction layer managing the PyVista plotter and VTK actors.

---

## 🛠 Critical Fixes & Stability

The application includes robust handling for common PyVista/Qt integration challenges:

1.  **Signal Storm Prevention**: (Fixed) UI updates (like navigation) are signal-blocked during refreshes to prevent infinite recursion loops and performance freezes.
2.  **VTK Actor Stability**: (Fixed) `SceneManager` uses an internal registry for actors to ensure precise cleanup, avoiding `RecursionError` and "ghost" actors persisting across files.
3.  **Redundant Load Optimization**: (Fixed) The 3D scene intelligently skips reloading STL files if the target mesh is already active, ensuring instantaneous shape management.
4.  **Modern PyVista Compatibility**: Uses explicit `inplace=True` transforms to ensure stability with latest PyVista versions.

---

## 💻 Tech Stack
- **Python 3.10+**
- **PyQt6**: Modern GUI framework.
- **PyVista / PyVistaQt**: High-performance 3D visualization.
- **NumPy**: Linear algebra for spatial transformations.

---

## 📖 How to Use
1.  **Open STL or URDF**: Load existing meshes manually or select `Browse URDF` in the left sidebar to automatically import all STL files from a robot description.
2.  **Resolve Packages**: If using ROS `package://` paths, the tool will attempt to resolve them automatically using sibling `/meshes` directory heuristics. If discovery fails, you will be prompted for a package root.
3.  **Add Shapes**: Select a mesh from the left panel and click `+ Add Shape` in the middle panel.
4.  **Refine**: Select the shape to adjust its dimensions, position, and rotation in the right panel. All edits are applied in the context of the mesh's URDF scale.
5.  **Navigate**: Use the `Previous` / `Next` buttons to process multiple files.
6.  **Export**: Click `Finish` to save URDF snippets, the project JSON, and a modified URDF with collisions injected.
