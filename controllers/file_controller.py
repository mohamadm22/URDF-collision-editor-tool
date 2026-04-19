"""
FileController — handles file loading, navigation, and state transitions.
Emits Qt signals consumed by the MainWindow.
"""

from __future__ import annotations
import os
from PyQt6.QtCore import QObject, pyqtSignal
from models.project_state import ProjectState
from models.mesh_model import MeshModel
from utils.urdf_parser import extract_meshes_from_urdf


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
                source="urdf"
            )
            self.state.meshes.append(mesh)
            summary["added"] += 1

        if summary["added"] > 0:
            self._emit_changed()

        return summary

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
            self.mesh_changed.emit(
                mesh,
                self.state.current_index,
                self.state.total,
            )
