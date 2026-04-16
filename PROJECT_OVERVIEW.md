# URDF Collision Editor - Project Documentation

This document serves as a comprehensive overview of the **URDF Collision Editor** project, designed to be easily understood by AI models or developers for maintenance, extension, or debugging.

---

## 1. Project Purpose
The **URDF Collision Editor** is a Python-based desktop application for creating and editing URDF collision geometries for STL mesh files. It provides an interactive 3D environment to approximate complex meshes with primitive shapes (Box, Cylinder, Sphere) and exports the resulting configuration in URDF-compatible formats.

---

## 2. Technology Stack
- **Language:** Python 3.10+
- **GUI Framework:** PyQt6
- **3D Visualization:** PyVista + PyVistaQt (specifically `QtInteractor`)
- **Data Handling:** NumPy
- **Serialization:** JSON (Project files), Text/XML (URDF snippets)

---

## 3. Architecture (MVC Pattern)

The project follows a strict separation of concerns using the Model-View-Controller pattern.

### A. Model Layer (`models/`)
- `project_state.py`: The single source of truth. Contains the list of all loaded meshes, the active mesh index, and the undo/redo stacks.
- `mesh_model.py`: Represents one STL file. Stores the file path and a list of collision shapes associated with it.
- `shapes/`:
    - `base_shape.py`: Abstract base class. Defines world-frame position, degree-based orientation, and common export logic.
    - `box_shape.py`, `cylinder_shape.py`, `sphere_shape.py`: Concrete implementations of collision primitives.

### B. Controller Layer (`controllers/`)
- `file_controller.py`: Manages loading STLs and navigating between files. Emits signals when the "active" file changes.
- `shape_controller.py`: Logic for adding, removing, and updating shapes. Each operation pushes a state snapshot to the undo stack.
- `export_controller.py`: Logic for generating URDF XML strings and saving the full project to JSON.

### C. View Layer (`views/`)
- `main_window.py`: Orchestrates all other widgets and initializes the 3D scene.
- `file_panel.py`: Left sidebar. Lists loaded STL files and highlights the active one.
- `shape_list_panel.py`: Bottom-middle panel. Shows shapes for the current file with Add/Delete buttons.
- `property_panel.py`: Right sidebar. Dynamically generates input fields based on the selected shape type.
- `visualization/scene_manager.py`: The bridge between the Model and the PyVista renderer.

---

## 4. Key Implementation Details

- **Coordinate Frame:** All coordinates are relative to the **World Origin**.
- **Orientation:** Displayed in **Degrees (Roll/Pitch/Yaw)** for human-friendliness but exported as **Radians** for URDF compatibility.
- **Batched Rendering:** All 3D updates use `render=False` for intermediate steps and a single `plotter.render()` at the end of an action to ensure high performance.
- **Actor Management:** `SceneManager` stores actual `vtkActor` objects (not name strings) to ensure reliable removal and to avoid ghost objects persisting across file switches.

---

## 5. Critical Fixes & Performance Notes (AI Context)

These are historical issues that were fixed and represent "gotchas" in the codebase:

1. **Performance (BackgroundPlotter vs. QtInteractor):**
    - **Problem:** Using `pyvistaqt.BackgroundPlotter` caused 5-second freezes because it runs VTK in a separate thread.
    - **Fix:** Switched to `pyvistaqt.QtInteractor`. This runs VTK in the same thread as the Qt main loop, which is much faster and more stable.
2. **Shape Isolation (Ghost Shapes):**
    - **Problem:** Shapes from "Part 1" would sometimes stay visible when switching to "Part 2".
    - **Fix:** `SceneManager.load_mesh` now explicitly calls `_clear_shapes()` BEFORE loading a new mesh. Actors are removed using the object reference, which is immune to name-string mismatches.
3. **Property Panel "Dead Clicks":**
    - **Problem:** Clicking a shape in the list that was already selected wouldn't reopen its properties.
    - **Fix:** Used `itemClicked` instead of `currentItemChanged` in `ShapeListPanel`.
4. **Parameter Limits:**
    - **Problem:** Parameters were hard-capped at 10.0 or 100.0.
    - **Fix:** All spinboxes in `PropertyPanel` now have a range of `±1,000,000` to be effectively unlimited.

---

## 6. Known Issues / Roadmap

- **Snap-to-Mesh:** Currently, shapes must be positioned manually. An auto-fitting or snapping algorithm would be a valuable extension.
- **Transform Gizmo:** Direct 3D manipulation of shapes using a mouse would improve UX.
- **Full URDF Export:** Currently exports snippets; needs logic to generate a full valid `.urdf` file with link name placeholders.

---

## 7. How to Extend
- **To add a new shape:** Subclass `BaseShape`, register it in `models/shapes/__init__.py`, update `PropertyPanel.load_shape()` to handle the new fields, and add a menu action in `ShapeListPanel._setup_ui()`.
