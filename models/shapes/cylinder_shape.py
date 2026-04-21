"""Cylinder collision shape."""

from __future__ import annotations
from dataclasses import dataclass, field
import pyvista as pv
from models.shapes.base_shape import BaseShape



@dataclass
class CylinderShape(BaseShape):
    name: str = "Cylinder"
    radius: float = 0.05
    length: float = 0.20
    color: tuple = field(default_factory=lambda: (0.2, 0.6, 1.0, 0.45))

    # ------------------------------------------------------------------ #
    def _extra_to_dict(self) -> dict:
        return {"radius": self.radius, "length": self.length}

    @classmethod
    def _from_dict_impl(cls, d: dict) -> "CylinderShape":
        obj = cls(
            id=d["id"],
            name=d["name"],
            radius=d["radius"],
            length=d["length"],
        )
        obj.position = d["position"]
        obj.orientation_deg = d["orientation_deg"]
        obj.color = tuple(d["color"])
        return obj

    # ------------------------------------------------------------------ #
    def to_urdf_geometry(self) -> str:
        return f'<cylinder radius="{self.radius:.6f}" length="{self.length:.6f}"/>'

    def to_pyvista_mesh(self):
        return self._apply_transform(self._create_raw_mesh())

    def _create_raw_mesh(self):
        # PyVista cylinder: axis along Z by default, centred at origin
        return pv.Cylinder(
            center=(0, 0, 0),
            direction=(0, 0, 1),
            radius=self.radius,
            height=self.length,
            resolution=36,
        )
