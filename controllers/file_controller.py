"""
FileController — handles file loading, navigation, and state transitions.
Emits Qt signals consumed by the MainWindow.
"""

from __future__ import annotations
from PyQt6.QtCore import QObject, pyqtSignal
from models.project_state import ProjectState
from models.mesh_model import MeshModel


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
            if not any(m.file_path == fp for m in self.state.meshes):
                self.state.meshes.append(MeshModel(fp))
        self._emit_changed()

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
