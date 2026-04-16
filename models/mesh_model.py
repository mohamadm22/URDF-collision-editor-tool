"""
MeshModel — holds the path to one STL file and all its collision shapes.
"""

from __future__ import annotations
import os
from dataclasses import dataclass, field
from models.shapes.base_shape import BaseShape
from models.shapes import SHAPE_REGISTRY


@dataclass
class MeshModel:
    file_path: str
    shapes: list = field(default_factory=list)   # list[BaseShape]

    @property
    def name(self) -> str:
        return os.path.basename(self.file_path)

    @property
    def stem(self) -> str:
        return os.path.splitext(self.name)[0]

    # ------------------------------------------------------------------ #
    def add_shape(self, shape: BaseShape) -> None:
        self.shapes.append(shape)

    def remove_shape(self, shape_id: str) -> None:
        self.shapes = [s for s in self.shapes if s.id != shape_id]

    def get_shape(self, shape_id: str) -> BaseShape | None:
        return next((s for s in self.shapes if s.id == shape_id), None)

    def replace_shape(self, shape: BaseShape) -> None:
        for i, s in enumerate(self.shapes):
            if s.id == shape.id:
                self.shapes[i] = shape
                return

    # ------------------------------------------------------------------ #
    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "shapes": [s.to_dict() for s in self.shapes],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MeshModel":
        obj = cls(file_path=d["file_path"])
        for sd in d.get("shapes", []):
            klass = SHAPE_REGISTRY.get(sd["type"])
            if klass:
                obj.shapes.append(klass._from_dict_impl(sd))
        return obj
