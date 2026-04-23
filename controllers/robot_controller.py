import os
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal
from models.robot_model import RobotModel, RobotVisualOrigin
from models.project_state import ProjectState
from models.collision_mapping import LinkCollisionData, CollisionOverlayData
from utils.urdf_visual_parser import parse_urdf_visuals
# from utils.debug_utils import trace_class_methods

class RobotController(QObject):
    """Orchestrates robot URDF parsing and triggers visualization signals."""
    
    robot_loaded = pyqtSignal(RobotModel, dict) # model, global_transforms
    robot_load_failed = pyqtSignal(str)
    robot_cleared = pyqtSignal()
    package_root_required = pyqtSignal(str) # Payload: urdf_path
    collision_overlay_ready = pyqtSignal(object) # Payload: CollisionOverlayData
    link_selection_requested = pyqtSignal(int, str)   # index into state.meshes, link_name
    link_focus_requested = pyqtSignal(str)       # link_name for camera

    def __init__(self, state: ProjectState, parent=None):
        super().__init__(parent)
        self._state = state
        self._current_model: RobotModel | None = None
        self._selected_frame: str = "map"
        self._link_to_mesh_index: dict[str, int] = {}

    def load_urdf(self, path: str, package_root: str | None = None):
        """Loads a URDF file and builds the robot visual model."""
        if not path:
            self.clear()
            return

        try:
            model = parse_urdf_visuals(path, package_root)
            self._current_model = model
            
            # Default frame logic
            if "map" in model.links:
                self._selected_frame = "map"
            elif model.links:
                # Fallback to root link if map not found (first link for now)
                self._selected_frame = list(model.links.keys())[0]

            # Check if we still have unresolved package paths
            has_unresolved = any("resolve" in w.lower() and "package://" in w.lower() for w in model.load_warnings)
            
            if has_unresolved and not package_root:
                self.package_root_required.emit(path)
                return

            self._refresh_visualization()
            # self.refresh_collision_overlay()
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.robot_load_failed.emit(str(e))

    def set_base_frame(self, frame_name: str):
        """Changes the reference frame for visualization."""
        if self._current_model and frame_name in self._current_model.links:
            self._selected_frame = frame_name
            self._refresh_visualization()

    def _refresh_visualization(self):
        if not self._current_model:
            return
        
        # print(f"[TRACE] RobotController._refresh_visualization - Frame: {self._selected_frame}")
            
        # 1. Compute global transforms relative to selected frame
        transforms = self._compute_global_transforms(self._current_model, self._selected_frame)
        self.robot_loaded.emit(self._current_model, transforms)

        # 2. Re-build and emit collision overlay (passing transforms to avoid re-computation)
        overlay = self._build_collision_overlay(transforms)
        if overlay:
            self.collision_overlay_ready.emit(overlay)

        # 3. Build link -> mesh index cache for picking
        self._build_link_to_mesh_index()

    def refresh_collision_overlay(self):
        """Called externally when collision shapes change in ProjectState."""
        if not self._current_model:
            return

        # print(f"[TRACE] RobotController.refresh_collision_overlay")
        transforms = self._compute_global_transforms(self._current_model, self._selected_frame)
        overlay = self._build_collision_overlay(transforms)
        if overlay:
            self.collision_overlay_ready.emit(overlay)

    def _build_collision_overlay(self, transforms: dict) -> CollisionOverlayData | None:
        """Constructs the overlay payload by mapping MeshModels to RobotLinks."""
        if not self._current_model or not self._state.meshes:
            return None

        # Build basename -> MeshModel lookup
        mesh_lookup = {os.path.basename(m.file_path): m for m in self._state.meshes}

        # Build link -> collision data mapping
        link_collisions = {}
        for link_name, link_model in self._current_model.links.items():
            for visual in link_model.visuals:
                if visual.type == "mesh" and visual.mesh_filename:
                    matched = mesh_lookup.get(visual.mesh_filename)
                    if matched and matched.shapes:
                        link_collisions[link_name] = LinkCollisionData(
                            link_name=link_name,
                            shapes=matched.shapes,
                            visual_scale=visual.scale,
                            visual_origin=visual.origin,
                            mesh_urdf_origin_xyz=matched.urdf_origin_xyz,
                            mesh_urdf_origin_rpy=matched.urdf_origin_rpy,
                            mesh_urdf_scale=matched.urdf_scale,
                        )

        return CollisionOverlayData(
            link_collisions=link_collisions,
            global_transforms=transforms
        )

    def _build_link_to_mesh_index(self):
        """Builds a cache mapping link names to their MeshModel index in state.meshes."""
        if not self._current_model or not self._state.meshes:
            self._link_to_mesh_index = {}
            return

        # Basename lookup for efficiency
        mesh_lookup = {os.path.basename(m.file_path): i for i, m in enumerate(self._state.meshes)}
        
        self._link_to_mesh_index = {}
        for link_name, link_model in self._current_model.links.items():
            for visual in link_model.visuals:
                if visual.type == "mesh" and visual.mesh_filename:
                    idx = mesh_lookup.get(visual.mesh_filename)
                    if idx is not None:
                        # Map the link to the FIRST matching mesh index found
                        self._link_to_mesh_index[link_name] = idx
                        break # One mesh per link for selection purposes

    def _on_link_single_clicked(self, link_name: str):
        """Slot for RobotSceneManager single-click event."""
        if not link_name: return
        idx = self._link_to_mesh_index.get(link_name)
        if idx is not None:
            self.link_selection_requested.emit(idx, link_name)

    def _on_link_double_clicked(self, link_name: str):
        """Slot for RobotSceneManager double-click event."""
        if not link_name: return
        # Dbl-click always triggers camera focus if the link exists
        if link_name in self._current_model.links:
            self.link_focus_requested.emit(link_name)

    def get_link_name_for_index(self, index: int) -> str | None:
        """Reverse lookup: find a link name that maps to a specific mesh index."""
        for link_name, idx in self._link_to_mesh_index.items():
            if idx == index:
                return link_name
        return None

    def _compute_global_transforms(self, model: RobotModel, base_frame: str) -> dict:
        """Calculates 4x4 global transforms for all links relative to base_frame."""
        # Simple implementation: build adjacency list from joints
        adj = {}
        for joint in model.joints:
            # parent -> child transform
            t = self._build_matrix(joint.origin)
            if joint.parent not in adj: adj[joint.parent] = []
            adj[joint.parent].append((joint.child, t))
            # child -> parent transform (inverse)
            inv_t = np.linalg.inv(t)
            if joint.child not in adj: adj[joint.child] = []
            adj[joint.child].append((joint.parent, inv_t))

        # BFS to find transforms to all other links
        transforms = {base_frame: np.eye(4)}
        queue = [base_frame]
        visited = {base_frame}

        while queue:
            curr = queue.pop(0)
            curr_t = transforms[curr]
            
            for child, rel_t in adj.get(curr, []):
                if child not in visited:
                    visited.add(child)
                    transforms[child] = curr_t @ rel_t
                    queue.append(child)
        
        return transforms

    def _build_matrix(self, origin: RobotVisualOrigin) -> np.ndarray:
        """Repeated small helper for matrix construction (avoids duplicate code)."""
        x, y, z = origin.xyz
        roll, pitch, yaw = origin.rpy
        rx = np.array([[1, 0, 0], [0, np.cos(roll), -np.sin(roll)], [0, np.sin(roll), np.cos(roll)]])
        ry = np.array([[np.cos(pitch), 0, np.sin(pitch)], [0, 1, 0], [-np.sin(pitch), 0, np.cos(pitch)]])
        rz = np.array([[np.cos(yaw), -np.sin(yaw), 0], [np.sin(yaw), np.cos(yaw), 0], [0, 0, 1]])
        r = rz @ ry @ rx
        t = np.eye(4)
        t[0:3, 0:3] = r
        t[0:3, 3] = [x, y, z]
        return t

    def clear(self):
        """Resets the robot visualization."""
        self._current_model = None
        self._link_to_mesh_index = {}
        self.robot_cleared.emit()
