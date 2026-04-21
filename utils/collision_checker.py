"""
Collision detection system for robot links.
Uses PyVista's collision filters to detect intersections between PolyData.
"""

from __future__ import annotations
import pyvista as pv
from typing import Dict, List, Tuple, Set

# from utils.debug_utils import trace_class_methods

class CollisionChecker:
    """Detects intersections between collision shapes in robot space."""
    
    def __init__(self):
        pass

    def check_all(self, link_meshes: Dict[str, List[pv.PolyData]]) -> Set[str]:
        """
        Check all pairs of links for collisions using AABB (axis-aligned bounding boxes).
        Returns a set of link names that are participating in at least one collision.
        """
        colliding_links = set()
        active_links = [n for n, m in link_meshes.items() if m]
        
        # Pre-compute combined bounds for each link to speed up pairwise checks
        link_bounds = {}
        for name in active_links:
            link_bounds[name] = self._combined_bounds(link_meshes[name])

        # Pairwise check between links
        for i in range(len(active_links)):
            for j in range(i + 1, len(active_links)):
                link_a = active_links[i]
                link_b = active_links[j]
                
                # Check if the overall bounding boxes of the two links overlap
                if self._aabb_overlap(link_bounds[link_a], link_bounds[link_b]):
                    colliding_links.add(link_a)
                    colliding_links.add(link_b)
                                
        return colliding_links

    def _combined_bounds(self, meshes: List[pv.PolyData]) -> List[float]:
        """Union bounding box of a list of meshes."""
        all_bounds = [m.bounds for m in meshes if m.n_points > 0]
        if not all_bounds:
            return [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        
        return [
            min(b[0] for b in all_bounds), max(b[1] for b in all_bounds), # X
            min(b[2] for b in all_bounds), max(b[3] for b in all_bounds), # Y
            min(b[4] for b in all_bounds), max(b[5] for b in all_bounds)  # Z
        ]

    def _aabb_overlap(self, b1: List[float], b2: List[float]) -> bool:
        """Check if two axis-aligned bounding boxes overlap."""
        return not (b1[1] < b2[0] or b1[0] > b2[1] or
                    b1[3] < b2[2] or b1[2] > b2[3] or
                    b1[5] < b2[4] or b1[4] > b2[5])
