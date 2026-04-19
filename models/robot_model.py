"""
RobotModel — data structures for robot visual representation.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict

@dataclass
class RobotVisualOrigin:
    """Stores raw URDF origin (xyz, rpy)."""
    xyz: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    rpy: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0]) # Radians

@dataclass
class RobotLinkVisual:
    """One visual entry for a single link (Mesh or Primitive)."""
    type: str = "mesh"  # "mesh", "box", "sphere", "cylinder"
    mesh_path: Optional[str] = None
    mesh_filename: str = ""
    # Primitive dimensions
    size: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0]) # [x, y, z] for box
    radius: float = 0.0 # for sphere/cylinder
    length: float = 0.0 # for cylinder
    
    origin: RobotVisualOrigin = field(default_factory=RobotVisualOrigin)
    scale: List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])

@dataclass
class RobotLinkModel:
    """One URDF link containing multiple visuals."""
    name: str
    visuals: List[RobotLinkVisual] = field(default_factory=list)

@dataclass
class RobotJointModel:
    """Represents a URDF joint connecting two frames."""
    name: str
    parent: str
    child: str
    origin: RobotVisualOrigin = field(default_factory=RobotVisualOrigin)
    type: str = "fixed"

@dataclass
class RobotModel:
    """The full robot visual model including frame tree."""
    urdf_path: str
    links: Dict[str, RobotLinkModel] = field(default_factory=dict) # link_name -> model
    joints: List[RobotJointModel] = field(default_factory=list)
    package_root: Optional[str] = None
    load_warnings: List[str] = field(default_factory=list)
    
    # Kinematic metadata
    base_frame: str = "map"
    # Helper to browse frames
    @property
    def frame_names(self) -> List[str]:
        return sorted(list(self.links.keys()))
