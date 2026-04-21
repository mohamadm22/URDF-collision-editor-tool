"""
Data transfer objects for collision overlay visualization.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, TYPE_CHECKING
import numpy as np

if TYPE_CHECKING:
    from models.shapes.base_shape import BaseShape
    from models.robot_model import RobotVisualOrigin

@dataclass
class LinkCollisionData:
    """Collision data for a single link, mapped from MeshModel."""
    link_name: str
    shapes: List[BaseShape]           # Reference to MeshModel.shapes
    visual_scale: List[float]         # [sx, sy, sz] from RobotLinkVisual
    visual_origin: RobotVisualOrigin  # From RobotLinkVisual
    mesh_urdf_origin_xyz: List[float] # From MeshModel
    mesh_urdf_origin_rpy: List[float] # From MeshModel
    mesh_urdf_scale: List[float]      # From MeshModel

@dataclass
class CollisionOverlayData:
    """Full payload for rendering the collision layer in Robot Viewer."""
    link_collisions: Dict[str, LinkCollisionData]   # link_name -> data
    global_transforms: Dict[str, np.ndarray]        # link_name -> 4x4 matrix
