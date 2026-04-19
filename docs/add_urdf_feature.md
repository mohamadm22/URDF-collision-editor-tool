# URDF Import + Collision Injection Feature

This project aims to extend the URDF Collision Editor tool to support importing an existing URDF file, matching its links with the created collision shapes based on STL mesh paths, and automatically injecting the `<collision>` blocks into a new modified URDF file.

## User Review Required

> [!IMPORTANT]
> The current plan modifies `ProjectState` and UI panels. Please review the specific locations for the new "URDF File Selector Panel". We'll place it at the bottom of the left sidebar (`FilePanel`). The existing export logic will be hooked to a new option or the existing "Finish" button process.

## Proposed Changes

---

### UI Layer / Views

#### [MODIFY] [views/file_panel.py](file:///home/youmad55/my%20github%20repos/URDF%20collision%20editor%20tool/views/file_panel.py)
- **Modifications**: Add a URDF File Selector Panel at the bottom of the `FilePanel`.
- It will contain a `QLabel` ("URDF File"), a read-only `QLineEdit`, and a `QPushButton` ("Browse").
- Wiring: Using `QFileDialog.getOpenFileName` it will emit a signal to the main window or store directly, but since we follow MVC, we should probably emit a signal so `MainWindow` updates `ProjectState.urdf_path` or handles it directly.

#### [MODIFY] [views/main_window.py](file:///home/youmad55/my%20github%20repos/URDF%20collision%20editor%20tool/views/main_window.py)
- **Modifications**: Update `_on_finish` slot.
- Read `urdf_path` from `self._state`.
- If `urdf_path` exists, trigger `self._export_ctrl.export_all_with_urdf(directory)` instead of `export_all`.

---

### Model Layer

#### [MODIFY] [models/project_state.py](file:///home/youmad55/my%20github%20repos/URDF%20collision%20editor%20tool/models/project_state.py)
- **Modifications**: 
- Add `urdf_path: Optional[str] = None` to `ProjectState` dataclass.
- Update `to_dict` and `from_dict` methods to serialize and deserialize `urdf_path`.

---

### Utilities / Processing

#### [NEW] [utils/urdf_modifier.py](file:///home/youmad55/my%20github%20repos/URDF%20collision%20editor%20tool/utils/urdf_modifier.py)
- **New Module**: Implements the XML parsing, mesh matching, scaling logic, and collision injection according to user constraints.
- Function: `generate_collision_urdf(original_urdf_path: str, meshes: list[MeshModel], output_path: str) -> str`
- Matches link meshes (`<mesh filename="...">`) against `MeshModel.file_path` (normalizing paths and handling `package://` prefix).
- Handles case where collision element might exist (replaces only if matched, leaving others intact).
- Applies `sx, sy, sz` scale from `<visual>` `<mesh>` by scaling shape position and size directly without altering orientation.

---

### Controller Layer

#### [MODIFY] [controllers/export_controller.py](file:///home/youmad55/my%20github%20repos/URDF%20collision%20editor%20tool/controllers/export_controller.py)
- **Modifications**:
- Add `export_full_urdf_with_collision(self, directory: str)` which invokes the `generate_collision_urdf` mechanism.
- Updates the main exporter logic to combine normal txt and json export with the injected URDF if `urdf_path` is present.

## Open Questions

> [!WARNING]
> Regarding shape scaling, how should a `Cylinder` and `Sphere` be scaled when non-uniform scales are given in the URDF `<mesh scale="sx sy sz"/>`? For shapes that restrict their parameterization (e.g., sphere radius), it's customary to take the maximum or average scale. I'll take the max scale for sphere radius, and X/Y max for cylinder radius + Z for cylinder length. Let me know if that is sufficient!

## Verification Plan

### Automated Tests
- The changes are strictly inside the desktop app, so testing will be primarily manual verification through the tool.

### Manual Verification
- Launch the application, load 2-3 STL files.
- Pick a valid URDF file.
- Verify that setting the URDF file path reflects correctly.
- Add shapes (Box, Cylinder) and then click Finish.
- Check the generated `<original>_with_collision.urdf` to ensure injected `<collision>` logic matches exactly and scale conversions behave correctly.
