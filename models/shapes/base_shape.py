"""
Base shape abstract class for all URDF collision primitives.
"""

from __future__ import annotations
import uuid
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
import numpy as np


def deg_to_rad(deg: float) -> float:
    return math.radians(deg)


def rad_to_deg(rad: float) -> float:
    return math.degrees(rad)


@dataclass
class BaseShape(ABC):
    """Abstract base for all collision geometry primitives."""

    # Identity
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Shape"

    # World-frame position [x, y, z] in metres
    position: list = field(default_factory=lambda: [0.0, 0.0, 0.0])

    # Orientation [roll, pitch, yaw] stored in DEGREES for the UI
    orientation_deg: list = field(default_factory=lambda: [0.0, 0.0, 0.0])

    # Visualization colour (R, G, B, A) 0–1
    color: tuple = field(default_factory=lambda: (0.2, 0.6, 1.0, 0.45))

    # ------------------------------------------------------------------ #
    # Public helpers                                                       #
    # ------------------------------------------------------------------ #

    @property
    def orientation_rad(self) -> list:
        """Return orientation as [roll, pitch, yaw] in radians (for URDF)."""
        return [deg_to_rad(d) for d in self.orientation_deg]

    def get_rpy_str(self) -> str:
        r, p, y = self.orientation_rad
        return f"{r:.6f} {p:.6f} {y:.6f}"

    def get_xyz_str(self) -> str:
        x, y, z = self.position
        return f"{x:.6f} {y:.6f} {z:.6f}"

    # ------------------------------------------------------------------ #
    # Serialisation                                                        #
    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict:
        return {
            "type": self.__class__.__name__,
            "id": self.id,
            "name": self.name,
            "position": self.position,
            "orientation_deg": self.orientation_deg,
            "color": list(self.color),
            **self._extra_to_dict(),
        }

    @abstractmethod
    def _extra_to_dict(self) -> dict:
        """Subclass-specific fields."""

    @classmethod
    def from_dict(cls, d: dict) -> "BaseShape":
        from models.shapes import SHAPE_REGISTRY
        klass = SHAPE_REGISTRY[d["type"]]
        return klass._from_dict_impl(d)

    @classmethod
    @abstractmethod
    def _from_dict_impl(cls, d: dict) -> "BaseShape":
        """Reconstruct instance from dict."""

    # ------------------------------------------------------------------ #
    # URDF                                                                 #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def to_urdf_geometry(self) -> str:
        """Return the inner <geometry> XML string."""

    def to_urdf_collision(self) -> str:
        return (
            f'<collision>\n'
            f'  <geometry>\n'
            f'    {self.to_urdf_geometry()}\n'
            f'  </geometry>\n'
            f'  <origin xyz="{self.get_xyz_str()}" rpy="{self.get_rpy_str()}"/>\n'
            f'</collision>'
        )

    # ------------------------------------------------------------------ #
    # PyVista mesh                                                         #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def to_pyvista_mesh(self):
        """Return a pyvista.PolyData representing this shape in world space."""

    def _apply_transform(self, mesh):
        """Translate mesh to world position (rotation handled by subclass)."""
        import pyvista as pv
        r, p, y = self.orientation_rad
        # Build 4×4 transform: Rz @ Ry @ Rx (yaw-pitch-roll convention)
        cos_r, sin_r = math.cos(r), math.sin(r)
        cos_p, sin_p = math.cos(p), math.sin(p)
        cos_y, sin_y = math.cos(y), math.sin(y)

        Rx = np.array([[1,0,0],[0,cos_r,-sin_r],[0,sin_r,cos_r]])
        Ry = np.array([[cos_p,0,sin_p],[0,1,0],[-sin_p,0,cos_p]])
        Rz = np.array([[cos_y,-sin_y,0],[sin_y,cos_y,0],[0,0,1]])
        R = Rz @ Ry @ Rx

        T = np.eye(4)
        T[:3, :3] = R
        T[:3, 3] = self.position
        return mesh.transform(T, inplace=True)
