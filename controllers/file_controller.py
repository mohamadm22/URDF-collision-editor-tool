"""
FileController — handles file loading, navigation, and state transitions.
Emits Qt signals consumed by the MainWindow.
"""

from __future__ import annotations
import os
import math
from PyQt6.QtCore import QObject, pyqtSignal
from models.project_state import ProjectState
from models.mesh_model import MeshModel
from models.shapes.stl_shape import StlShape
from utils.urdf_parser import extract_meshes_from_urdf, extract_collision_shapes_from_urdf
from utils.debug_utils import trace_class_methods

class FileController(QObject):
    # Emitted when the active mesh changes: (MeshModel, index, total)
    mesh_changed = pyqtSignal(object, int, int)

    def __init__(self, state: ProjectState, parent=None):
        super().__init__(parent)
        self.state = state

    # ------------------------------------------------------------------ #
    # Load                                                                 #
    # ------------------------------------------------------------------ #

    def load_files(self, paths: list) -> None:
        """Replace the mesh list with newly selected files."""
        self.state.meshes = [MeshModel(fp) for fp in paths]
        self.state.current_index = 0
        self._emit_changed()

    def append_files(self, paths: list) -> None:
        """Append new STL files to an existing session."""
        for fp in paths:
            if not self._is_duplicate(fp):
                self.state.meshes.append(MeshModel(fp))
        self._emit_changed()

    def import_urdf_meshes(self, urdf_path: str, package_root: str = None) -> dict:
        """Parse URDF and add all new meshes to the project."""
        try:
            mesh_data = extract_meshes_from_urdf(urdf_path, package_root)
        except Exception as e:
            return {"error": str(e)}

        summary = {
            "added": 0,
            "skipped_duplicate": 0,
            "missing_file": [],
            "needs_package_root": False
        }

        for data in mesh_data:
            path = data["resolved_path"]
            if not data["is_resolved"]:
                summary["missing_file"].append(data["raw_path"])
                if data["raw_path"].startswith("package://"):
                    summary["needs_package_root"] = True
                continue

            if self._is_duplicate(path):
                summary["skipped_duplicate"] += 1
                continue

            # Create new mesh model with URDF metadata
            mesh = MeshModel(
                file_path=path,
                urdf_scale=data["scale"],
                urdf_origin_xyz=data["origin_xyz"],
                urdf_origin_rpy=data["origin_rpy"],
                source="urdf"
            )
            self.state.meshes.append(mesh)
            summary["added"] += 1

        if summary["added"] > 0:
            # Attach collision shapes for newly added or existing meshes
            self._attach_collision_shapes(urdf_path, package_root)
            self._emit_changed()

        return summary

    def _attach_collision_shapes(self, urdf_path: str, package_root: str = None) -> None:
        """Parse URDF for collision meshes and attach them to corresponding MeshModels."""
        try:
            collision_data = extract_collision_shapes_from_urdf(urdf_path, package_root)
        except Exception:
            return

        # Prepare basename lookup for our loaded MeshModels
        # link visuals in URDF usually point to meshes via package://pkg/meshes/file.stl
        # our MeshModels store the resolved absolute path
        # we'll match by file basename to be robust
        mesh_lookup = {os.path.basename(m.file_path): m for m in self.state.meshes}

        # We also need to know which link uses which visual mesh in the URDF 
        # to correctly associate collision shapes (which are per-link) with our MeshModels.
        try:
            visual_mesh_data = extract_meshes_from_urdf(urdf_path, package_root)
        except Exception:
            return

        # Map link names to visual mesh basenames
        # Note: URDF parsing above doesn't preserve link name in extract_meshes_from_urdf
        # I should probably update extract_meshes_from_urdf to include link_name,
        # but I can also just re-parse here or assume a simpler mapping if possible.
        # Actually, let's fix extract_meshes_from_urdf to include link name for better matching.
        # Wait, I'll just do a quick parse here to get the link -> visual mapping.
        from lxml import etree
        try:
            tree = etree.parse(urdf_path)
            root = tree.getroot()
            link_to_visual_base = {}
            for link in root.xpath("//link"):
                lname = link.get("name")
                vmesh = link.xpath(".//visual//geometry//mesh")
                if lname and vmesh:
                    fname = vmesh[0].get("filename")
                    if fname:
                        link_to_visual_base[lname] = os.path.basename(fname)
        except Exception:
            return

        for link_name, shapes in collision_data.items():
            visual_base = link_to_visual_base.get(link_name)
            if not visual_base:
                continue
                
            mesh_model = mesh_lookup.get(visual_base)
            if not mesh_model:
                continue

            for s_data in shapes:
                if not s_data["is_resolved"]:
                    continue
                    
                # Deduplication
                path = s_data["resolved_path"]
                if any(isinstance(s, StlShape) and s.stl_path == path for s in mesh_model.shapes):
                    continue

                v_scale = mesh_model.urdf_scale
                v_origin_xyz = mesh_model.urdf_origin_xyz
                
                # Normalize position: display_pos = (urdf_coll_pos - visual_urdf_pos) / visual_scale
                # This ensures the collision remains relative to the visual mesh base.
                display_pos = []
                for i in range(3):
                    offset = s_data["origin_xyz"][i] - v_origin_xyz[i]
                    if v_scale[i] != 0:
                        display_pos.append(offset / v_scale[i])
                    else:
                        display_pos.append(offset)
                

                stl_shape = StlShape(
                    name=f"STL_{os.path.basename(path)}",
                    stl_path=path,
                    raw_urdf_path=s_data["raw_path"],
                    urdf_visual_scale=mesh_model.urdf_scale,
                    scale=[1.0, 1.0, 1.0] # Default user scale
                )
                stl_shape.position = display_pos
                rpy_rad = s_data["origin_rpy"]
                stl_shape.orientation_deg = [math.degrees(r) for r in rpy_rad]
                
                mesh_model.add_shape(stl_shape)

    def _is_duplicate(self, file_path: str) -> bool:
        """Check if mesh is already loaded by filename or path."""
        new_norm = os.path.normpath(file_path)
        new_base = os.path.basename(file_path)

        for mesh in self.state.meshes:
            if os.path.normpath(mesh.file_path) == new_norm:
                return True
            if os.path.basename(mesh.file_path) == new_base:
                return True
        return False

    # ------------------------------------------------------------------ #
    # Navigation                                                           #
    # ------------------------------------------------------------------ #

    def navigate_to(self, index: int) -> None:
        if self.state.navigate_to(index):
            self._emit_changed()

    def next_file(self) -> None:
        self.navigate_to(self.state.current_index + 1)

    def prev_file(self) -> None:
        self.navigate_to(self.state.current_index - 1)

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _emit_changed(self):
        mesh = self.state.current_mesh
        if mesh is not None:
            print(f"[TRACE] FileController.mesh_changed EMIT")
            self.mesh_changed.emit(
                mesh,
                self.state.current_index,
                self.state.total,
            )
