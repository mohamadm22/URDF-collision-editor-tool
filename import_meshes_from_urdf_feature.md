# Feature Design: Auto-Import STL Meshes from URDF

This document outlines the architectural and step-by-step implementation plan for automatically importing STL collision geometries from a linked URDF file in the URDF Collision Editor. 

---

## 1. NEW / UPDATED DATA STRUCTURES

### `MeshModel` (`models/mesh_model.py`)
To ensure that scaling operations specified inside the URDF are preserved and applied during the collision generation phase, we must capture this metadata at the mesh level upon import.

* Add `urdf_scale: list[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])`
* Add `source: str = "manual"` (can be `"manual"` or `"urdf"`) to distinguish how the file was ingested.
* **Update `to_dict` / `from_dict`**: Ensure these fields are explicitly serialized for persistent JSON project storage.

### `ProjectState` (`models/project_state.py`)
No fundamental shift is needed here as `ProjectState` already delegates mesh storage to `MeshModel`.

---

## 2. NEW MODULES OR FUNCTIONS

### `utils/urdf_parser.py`
A new dedicated utility module for analyzing URDF layouts independently of the GUI constraints.

**Target Functions:**
* `extract_meshes_from_urdf(urdf_path: str, package_root: str | None = None) -> list[dict]`
  * Queries `<visual><geometry><mesh>` tags.
  * Captures filename and `scale="sx sy sz"`.
  * Normalizes the path using the resolver function. Returns dictionaries containing `{"absolute_path": ..., "scale": ..., "filename": ...}`.
* `resolve_mesh_path(raw_path: str, urdf_dir: str, package_root: str | None) -> str`
  * Handles standard relative and absolute paths.

---

## 3. CONTROLLER CHANGES

### `FileController` (`controllers/file_controller.py`)
This controller is the steward of mesh array logic. We encapsulate URDF imports here to prevent leaking logic to the View.

**Target Function:**
* `import_urdf_meshes(self, urdf_path: str, package_root: str | None = None) -> dict`
  * **Responsibilities**: 
    1. Calls the `urdf_parser` to get raw mesh dicts.
    2. Runs deduplication checks.
    3. If valid, provisions a `MeshModel(file_path=path)`.
    4. Applies `model.urdf_scale = scale` and `model.source = "urdf"`.
    5. Appends to `self.state.meshes` and emits `mesh_changed`.
  * **Returns**: A summary dictionary `{"added_count": int, "missing_files": list[str], "needs_package_root": bool}`.

---

## 4. PATH NORMALIZATION STRATEGY

To resolve references and properly evaluate duplicates:
1. **Absolute Paths (`/home/...`)**: Returned as-is.
2. **Relative Paths (`../meshes/part.stl`)**: Resolved relative to the directory containing the source `.urdf` file using `os.path.normpath(os.path.join(urdf_dir, raw_path))`.
3. **Package Paths (`package://pkg_name/meshes/...`)**: 
   * The prefix `package://` is stripped.
   * If `package_root` is provided, standard resolution proceeds: `os.path.normpath(os.path.join(package_root, stripped_path))`.
   * If `package_root` is *not* provided, the system skips and returns a state indicating the root is required.

---

## 5. DUPLICATE DETECTION LOGIC

Strictly evaluated inside `FileController` against `ProjectState.meshes` before appending:

* **Primary Key (Filename):** Compare `os.path.basename(new_path) == os.path.basename(existing_mesh.file_path)`.
* **Secondary Key (Path):** Compare `os.path.normpath(new_path) == os.path.normpath(existing_mesh.file_path)`.

*If EITHER condition resolves to True, the mesh is discarded as a duplicate to ensure part modularity is respected, even if loaded via different symlinks or directories.*

---

## 6. ERROR HANDLING

Errors must bubble up gracefully without crashing the UI.

* **Invalid URDF structure:** The parser catches `lxml.etree.XMLSyntaxError` and raises a standard `ValueError("Invalid or corrupt URDF XML")`.
* **Missing Files on Disk:** If `os.path.exists(resolved_path)` is false, it is skipped and appended to the `missing_files` list returned to the UI.
* **Unresolved Package Paths:** If `package://` encounters a `None` `package_root`, the controller gracefully bails out but returns `needs_package_root: True`.

---

## 7. STEP-BY-STEP IMPLEMENTATION PLAN

* **Phase 1: Scale and State Updates**
  * Modify `MeshModel` to store and serialize `urdf_scale` and `source`.
* **Phase 2: Parsing & Absolute Path Resolution (`urdf_parser.py`)** 
  * Develop logic to extract visual meshes, handle multiple `scale` fallbacks, and resolve strings using `os.path`.
* **Phase 3: Controller Aggregation (`FileController.py`)**
  * Integrate parsing logic mapped with duplicate protection. Return structured summary payloads for UI consumption.
* **Phase 4: View Layer Wiring (`MainWindow.py`)**
  * Hook the `urdf_selected` signal.
  * In `MainWindow`, attempt `import_urdf_meshes`.
  * If `needs_package_root`, trigger `QFileDialog.getExistingDirectory()` to ask the user to point to their Catkin/Colcon ROS workspace, then retry the load.
  * Output `QMessageBox` summarizing the successes and ignored mesh files.

---

## 8. CLEAN ARCHITECTURE RULES

* **No UI in Model/Controller**: Errors are handled by returning clear states (`needs_package_root`, `missing_files`) for the Qt frontend to process with dialog boxes.
* **Separation of parsing**: Pure python utility functions (`urdf_parser.py`) testable outside of PyQt.
* **No Breaking Workflows**: The manual `<Add STL>` flow inside `FileController.append_files` remains functionally pristine and completely separate from `import_urdf_meshes`.
