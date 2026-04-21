"""Box collision shape."""

from __future__ import annotations
from dataclasses import dataclass, field
import pyvista as pv
from models.shapes.base_shape import BaseShape



@dataclass
class BoxShape(BaseShape):
    name: str = "Box"
    size_x: float = 0.10
    size_y: float = 0.10
    size_z: float = 0.10
    color: tuple = field(default_factory=lambda: (0.2, 0.9, 0.4, 0.45))

    def _extra_to_dict(self) -> dict:
        return {"size_x": self.size_x, "size_y": self.size_y, "size_z": self.size_z}

    @classmethod
    def _from_dict_impl(cls, d: dict) -> "BoxShape":
        obj = cls(
            id=d["id"],
            name=d["name"],
            size_x=d["size_x"],
            size_y=d["size_y"],
            size_z=d["size_z"],
        )
        obj.position = d["position"]
        obj.orientation_deg = d["orientation_deg"]
        obj.color = tuple(d["color"])
        return obj

    def to_urdf_geometry(self) -> str:
        return f'<box size="{self.size_x:.6f} {self.size_y:.6f} {self.size_z:.6f}"/>'

    def to_pyvista_mesh(self):
        return self._apply_transform(self._create_raw_mesh())

    def _create_raw_mesh(self):
        return pv.Box(
            bounds=(
                -self.size_x / 2, self.size_x / 2,
                -self.size_y / 2, self.size_y / 2,
                -self.size_z / 2, self.size_z / 2,
            )
        )
