"""
ProjectState — global application state: all loaded meshes, active index,
undo/redo history, and project path.
"""

from __future__ import annotations
import copy
from dataclasses import dataclass, field
from typing import Optional
from models.mesh_model import MeshModel


@dataclass
class ProjectState:
    meshes: list = field(default_factory=list)   # list[MeshModel]
    current_index: int = 0
    project_path: Optional[str] = None

    # Undo / redo stacks store deep-copy snapshots of meshes list
    _undo_stack: list = field(default_factory=list, repr=False)
    _redo_stack: list = field(default_factory=list, repr=False)

    # ------------------------------------------------------------------ #
    # Navigation helpers                                                   #
    # ------------------------------------------------------------------ #

    @property
    def current_mesh(self) -> Optional[MeshModel]:
        if 0 <= self.current_index < len(self.meshes):
            return self.meshes[self.current_index]
        return None

    @property
    def is_first(self) -> bool:
        return self.current_index == 0

    @property
    def is_last(self) -> bool:
        return self.current_index >= len(self.meshes) - 1

    @property
    def total(self) -> int:
        return len(self.meshes)

    def navigate_to(self, index: int) -> bool:
        if 0 <= index < len(self.meshes):
            self.current_index = index
            return True
        return False

    # ------------------------------------------------------------------ #
    # Undo / Redo                                                         #
    # ------------------------------------------------------------------ #

    def _snapshot(self) -> list:
        return copy.deepcopy([m.to_dict() for m in self.meshes])

    def push_undo(self) -> None:
        self._undo_stack.append(self._snapshot())
        self._redo_stack.clear()

    def undo(self) -> bool:
        if not self._undo_stack:
            return False
        self._redo_stack.append(self._snapshot())
        snapshot = self._undo_stack.pop()
        self.meshes = [MeshModel.from_dict(d) for d in snapshot]
        return True

    def redo(self) -> bool:
        if not self._redo_stack:
            return False
        self._undo_stack.append(self._snapshot())
        snapshot = self._redo_stack.pop()
        self.meshes = [MeshModel.from_dict(d) for d in snapshot]
        return True

    # ------------------------------------------------------------------ #
    # Serialisation                                                        #
    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict:
        return {
            "current_index": self.current_index,
            "meshes": [m.to_dict() for m in self.meshes],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ProjectState":
        obj = cls(current_index=d.get("current_index", 0))
        obj.meshes = [MeshModel.from_dict(md) for md in d.get("meshes", [])]
        return obj
