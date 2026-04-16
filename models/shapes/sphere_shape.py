"""Sphere collision shape."""

from __future__ import annotations
from dataclasses import dataclass, field
import pyvista as pv
from models.shapes.base_shape import BaseShape



@dataclass
class SphereShape(BaseShape):
    name: str = "Sphere"
    radius: float = 0.05
    color: tuple = field(default_factory=lambda: (1.0, 0.5, 0.1, 0.45))

    def _extra_to_dict(self) -> dict:
        return {"radius": self.radius}

    @classmethod
    def _from_dict_impl(cls, d: dict) -> "SphereShape":
        obj = cls(id=d["id"], name=d["name"], radius=d["radius"])
        obj.position = d["position"]
        obj.orientation_deg = d["orientation_deg"]
        obj.color = tuple(d["color"])
        return obj

    def to_urdf_geometry(self) -> str:
        return f'<sphere radius="{self.radius:.6f}"/>'

    def to_pyvista_mesh(self):
        # Sphere has no orientation (it's symmetric) but we still apply
        # the position translation via _apply_transform
        mesh = pv.Sphere(radius=self.radius, center=(0, 0, 0), theta_resolution=24, phi_resolution=24)
        return self._apply_transform(mesh)
