"""StlShape collision geometry."""

from __future__ import annotations
import os
import math
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
import pyvista as pv
from models.shapes.base_shape import BaseShape


@dataclass
class StlShape(BaseShape):
    name: str = "STL_Shape"
    stl_path: str = ""
    scale: list[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])
    urdf_visual_scale: list[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])
    raw_urdf_path: str = ""
    color: tuple = field(default_factory=lambda: (0.2, 0.9, 0.4, 0.45)) # Green

    def _extra_to_dict(self) -> dict:
        return {
            "stl_path": self.stl_path,
            "scale": self.scale,
            "urdf_visual_scale": self.urdf_visual_scale,
            "raw_urdf_path": self.raw_urdf_path,
        }

    @classmethod
    def _from_dict_impl(cls, d: dict) -> "StlShape":
        obj = cls(
            id=d["id"],
            name=d["name"],
            stl_path=d.get("stl_path", ""),
            scale=d.get("scale", [1.0, 1.0, 1.0]),
            urdf_visual_scale=d.get("urdf_visual_scale", [1.0, 1.0, 1.0]),
            raw_urdf_path=d.get("raw_urdf_path", ""),
        )
        obj.position = d["position"]
        obj.orientation_deg = d["orientation_deg"]
        obj.color = tuple(d["color"])
        return obj

    def to_urdf_geometry(self) -> str:
        # Export rule: final_export_scale = user_scale * urdf_visual_scale
        s = [self.scale[i] * self.urdf_visual_scale[i] for i in range(3)]
        return f'<mesh filename="{self.raw_urdf_path}" scale="{s[0]:.6f} {s[1]:.6f} {s[2]:.6f}"/>'

    def to_pyvista_mesh(self):
        if not self.stl_path or not os.path.exists(self.stl_path):
            return pv.PolyData()
            
        try:
            mesh = pv.read(self.stl_path)
            
            # Display scale is now directly the user scale (scale 1 normalized)
            mesh.scale(self.scale, inplace=True)
            return self._apply_transform(mesh)
        except Exception as e:
            print(f"[StlShape] Error loading mesh: {e}")
            return pv.PolyData()
