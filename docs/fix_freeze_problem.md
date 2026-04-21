# URDF Collision Editor — Performance Fix & Feature Implementation Plan

## Diagnosis: Why the Program Is Being Killed

The log shows the program runs for ~30 seconds after import and then is **killed by the OS (OOM killer)**. I've traced the exact chain of events:

### Root Cause 1: `pv.PolyData.collision()` Causes VTK Jacobi Errors → OOM Kill

The `vtkMath::Jacobi: Error extracting eigenfunctions` warnings come **directly from PyVista's narrow-phase collision API** (`calc_a.collision(calc_b)` in `collision_checker.py:49`).  

This happens because:
1. On URDF import, ~100+ collision shapes are added
2. `ShapeController.shapes_changed` fires → `RobotController.refresh_collision_overlay()` → `render_collision_layer()` → `_collision_check_timer` fires → `CollisionWorker` starts
3. `CollisionWorker` calls `CollisionChecker.check_all()` which calls `pv.collision()` on potentially tiny or degenerate geometry (STL shapes with zero-scale or flat surfaces)
4. **`pv.collision()` internally calls VTK's `vtkOBBTree` which uses Jacobi iteration** — this fails on degenerate meshes, spams warnings, and causes massive GPU/CPU spikes
5. After enough iterations, Linux OOM-kills the process

### Root Cause 2: Full Re-render of All Visual Meshes on Every Overlay Update

In `RobotSceneManager.render_robot()`, **every call to `render_collision_layer()` is preceded by a full `render_robot()` call** (via `_refresh_visualization()`), which:
- Clears and re-adds all ~80 STL mesh actors
- Creates transformed copies of all visual meshes (expensive copying)
- Calls `plotter.render()` after every single shape

This means importing a URDF re-draws the entire robot 3+ times redundantly.

---

## User Review Required

> [!WARNING]
> **Collision Detection Strategy Change**: The `pv.PolyData.collision()` narrow-phase check is the direct cause of the VTK Jacobi crashes. The plan replaces it with a **pure AABB-only collision detection** approach. AABB (bounding box) is much faster and will not crash, but will produce some false positives (two shapes whose bounding boxes overlap but don't actually touch). We can add back narrow-phase optionally later with sanitization. Please confirm this is acceptable.

> [!IMPORTANT]
> **Full Robot Re-render Strategy**: Currently the code re-renders all ~80 visual meshes every time a collision shape changes. The plan adds a **separate collision-only render path** so editing shapes only redraws the collision layer, not the visuals. This is the biggest performance win.

---

## Proposed Changes

### Phase 1 (Critical): Fix the Crash — Replace Unsafe Collision Check

#### [MODIFY] [collision_checker.py](file:///home/youmad55/my%20github%20repos/URDF%20collision%20editor%20tool/utils/collision_checker.py)

**Problem**: `pv.PolyData.collision()` on degenerate meshes causes Jacobi errors and OOM.

**Fix**: Replace the narrow-phase `calc_a.collision(calc_b)` with **AABB-only detection**. This is safe, fast (no VTK eigenfunction computation), and will not crash.

```python
def check_all(self, link_meshes: dict) -> set:
    colliding = set()
    links = [n for n, m in link_meshes.items() if m]
    for i in range(len(links)):
        for j in range(i+1, len(links)):
            # Only AABB — fast, no VTK calls, no crash
            bounds_a = self._combined_bounds(link_meshes[links[i]])
            bounds_b = self._combined_bounds(link_meshes[links[j]])
            if self._aabb_overlap(bounds_a, bounds_b):
                colliding.add(links[i])
                colliding.add(links[j])
    return colliding

def _combined_bounds(self, meshes):
    """Union bounding box of a list of meshes."""
    all_bounds = [m.bounds for m in meshes if m.n_points > 0]
    if not all_bounds: return [0]*6
    return [min(b[0] for b in all_bounds), max(b[1] for b in all_bounds),
            min(b[2] for b in all_bounds), max(b[3] for b in all_bounds),
            min(b[4] for b in all_bounds), max(b[5] for b in all_bounds)]
```

The `_proxy_cache` and `decimate()` can be removed entirely since they're no longer needed.

---

### Phase 2 (Performance): Decouple Visual and Collision Rendering

#### [MODIFY] [robot_scene_manager.py](file:///home/youmad55/my%20github%20repos/URDF%20collision%20editor%20tool/visualization/robot_scene_manager.py)

**Problem**: `render_robot()` adds a `reset_camera()` and destroys/recreates all 80 actors on every collision update.

**Fix**: 
1. Store the `RobotModel` and `transforms` so `render_collision_layer()` can be called independently without triggering a full visual remake.
2. Add a **mesh STL loading cache** so `pv.read()` is only called once per file path.
3. Remove `reset_camera()` from repeating calls — only call it on initial URDF load.

**Key change**: `render_robot()` will be renamed `render_visual_layer()` internally and will store last-rendered model state. `render_collision_layer()` is completely independent.

---

### Phase 3 (Performance): Suppress VTK Output Noise

#### [MODIFY] [main.py](file:///home/youmad55/my%20github%20repos/URDF%20collision%20editor%20tool/main.py)

Add VTK output window suppression at startup to prevent the Jacobi warnings from flooding stderr even if they somehow occur:

```python
import vtk
output = vtk.vtkStringOutputWindow()
vtk.vtkOutputWindow.SetInstance(output)
```

---

### Phase 4: Complete the Feature — Collision Layer Rendering (Already Partially Done)

The collision overlay system is **already wired** (`CollisionOverlayData`, `render_collision_layer()`, signals) but has a bug in `_create_collision_primitive_mesh` for STL shapes. The current code has a logic error:

```python
# CURRENT BUG in robot_scene_manager.py:184-219
elif isinstance(shape, StlShape):
    if shape.stl_path in self._mesh_cache:
        mesh = self._mesh_cache[shape.stl_path].copy()
        mesh.scale(shape.scale, inplace=True)
    else:
        mesh = shape._create_raw_mesh()   # ← _create_raw_mesh() already applies scale!
        # No cache store! Every call re-reads from disk!
        pass
```

**Fix**: Properly cache STL mesh reads and avoid double-scaling.

---

### Phase 5: Clean Up Remaining Debug Traces

#### [MODIFY] Multiple files

Remove `print(f"[TRACE] ...")` statements from:
- `robot_controller.py:66` — `_refresh_visualization`
- `robot_controller.py:82` — `refresh_collision_overlay`  
- `main_window.py:399` — `_run_urdf_import START`
- `main_window.py:447` — `_run_urdf_import END`
- `main_window.py:450` — `_on_collision_overlay_ready`
- `main_window.py:482` — `_on_robot_loaded`
- `robot_viewer_panel.py:68` — `update_model`

Remove unused import of `trace_class_methods` from:
- `collision_checker.py:10`
- `robot_scene_manager.py:11`
- `robot_controller.py:8`
- `shape_controller.py:17`
- `main_window.py:52`

---

## Current Feature Status vs. Plan

| Feature Section | Status | Gap |
|---|---|---|
| Data DTOs (`CollisionOverlayData`) | ✅ Done | — |
| `RobotController._build_collision_overlay()` | ✅ Done | — |
| `collision_overlay_ready` signal | ✅ Done | — |
| `render_collision_layer()` in SceneManager | ✅ Done but buggy | STL cache bug, redundant render |
| UI Toggles (Visual/Collision checkboxes) | ✅ Done | — |
| `ShapeController.shapes_changed` signal | ✅ Done | — |
| Live update wiring | ✅ Done | — |
| `highlight_collisions()` (red/green) | ✅ Done | — |
| `CollisionChecker` | ✅ Done | **Crashes on degenerate geometry** |
| VTK noise suppression | ❌ Missing | Needs 1-line fix in `main.py` |
| STL mesh cache in overlay render | ❌ Buggy | Reads disk every render call |
| Reset camera on every update | ❌ Regression | Only call on first load |

---

## Verification Plan

### After Phase 1 (Crash Fix)
- Import InMoov URDF → program should no longer be killed
- Jacobi warnings should disappear from stderr

### After Phase 2 (Performance)
- Edit a collision shape → only the collision layer updates, not all 80 visual meshes
- Time from URDF import to UI responsive should be under 5 seconds

### After Phase 4 (Feature)
- Load URDF + import meshes + add a Box shape → box appears in robot viewer at the correct link location
- Toggle "Collision Shapes" checkbox → shapes disappear/reappear
- Move a shape → robot viewer updates within 300ms
- Position two shapes on adjacent links to overlap → they turn red

### Manual Verification Checklist
- [ ] InMoov URDF imports without crash
- [ ] Status bar shows "Collision check: OK" or "⚠️ Collision detected"
- [ ] Red highlighting works for overlapping links
- [ ] Visual/Collision checkboxes work independently
- [ ] Undo/Redo updates the robot viewer
