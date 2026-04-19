import os
import pyvista as pv
import numpy as np
from typing import Optional, Dict, List
from models.robot_model import RobotModel, RobotVisualOrigin, RobotLinkVisual

class RobotSceneManager:
    """Manages robot visualization in a dedicated plotter."""

    def __init__(self, plotter):
        self.plotter = plotter
        # Key: "actor_id", Value: actor
        self._actors: Dict[str, pv.Actor] = {}
        self._configure_plotter()

    def _configure_plotter(self):
        self.plotter.set_background("#111b27")
        self.plotter.add_axes(line_width=2)

    def render_robot(self, model: RobotModel, global_transforms: Dict[str, np.ndarray]) -> None:
        """Clears and renders the full robot model using global transforms."""
        self.clear_robot()
        
        for link_name, link in model.links.items():
            # Get global transform for this link
            base_t = global_transforms.get(link_name)
            if base_t is None:
                continue

            for i, visual in enumerate(link.visuals):
                try:
                    # 1. Create mesh (from file or primitive)
                    mesh = self._create_visual_mesh(visual)
                    if mesh is None:
                        continue
                        
                    # 2. Add per-visual origin transform
                    origin_t = self._build_transform_matrix(visual.origin)
                    
                    # 3. Apply global link transform
                    final_t = base_t @ origin_t
                    mesh.transform(final_t, inplace=True)
                    
                    # 4. Add to plotter
                    actor_id = f"{link_name}__{i}"
                    actor = self.plotter.add_mesh(
                        mesh,
                        color="#a0b0c0",
                        opacity=0.8,
                        name=actor_id,
                        smooth_shading=True,
                        lighting=True,
                        render=False
                    )
                    self._actors[actor_id] = actor
                    
                except Exception as e:
                    print(f"[RobotSceneManager] Failed to render visual {i} of {link_name}: {e}")
        
        self.plotter.reset_camera()
        self.plotter.render()

    def _create_visual_mesh(self, visual: RobotLinkVisual) -> Optional[pv.PolyData]:
        """Creates a PyVista mesh for the given visual entry."""
        if visual.type == "mesh":
            if not visual.mesh_path or not os.path.exists(visual.mesh_path):
                return None
            mesh = pv.read(visual.mesh_path)
            if any(s != 1.0 for s in visual.scale):
                mesh.scale(visual.scale, inplace=True)
            return mesh
            
        elif visual.type == "box":
            # size is [x, y, z]
            return pv.Box(bounds=(
                -visual.size[0]/2, visual.size[0]/2,
                -visual.size[1]/2, visual.size[1]/2,
                -visual.size[2]/2, visual.size[2]/2
            ))
            
        elif visual.type == "sphere":
            return pv.Sphere(radius=visual.radius)
            
        elif visual.type == "cylinder":
            # cylinder in PV is along Z by default if given height
            return pv.Cylinder(radius=visual.radius, height=visual.length, direction=(0, 0, 1))
            
        return None

    def clear_robot(self):
        """Removes all robot actors."""
        for actor_id in list(self._actors.keys()):
            try:
                self.plotter.remove_actor(actor_id, render=False)
            except Exception:
                pass
        self._actors.clear()
        self.plotter.render()

    def reset_camera(self):
        self.plotter.reset_camera()
        self.plotter.render()

    def _build_transform_matrix(self, origin: RobotVisualOrigin) -> np.ndarray:
        """Builds a 4x4 homogeneous transform matrix from URDF origin."""
        x, y, z = origin.xyz
        roll, pitch, yaw = origin.rpy
        
        # Rotation matrices
        rx = np.array([
            [1, 0, 0],
            [0, np.cos(roll), -np.sin(roll)],
            [0, np.sin(roll), np.cos(roll)]
        ])
        
        ry = np.array([
            [np.cos(pitch), 0, np.sin(pitch)],
            [0, 1, 0],
            [-np.sin(pitch), 0, np.cos(pitch)]
        ])
        
        rz = np.array([
            [np.cos(yaw), -np.sin(yaw), 0],
            [np.sin(yaw), np.cos(yaw), 0],
            [0, 0, 1]
        ])
        
        # URDF order: Rz * Ry * Rx
        r = rz @ ry @ rx
        
        # Homogeneous matrix
        t = np.eye(4)
        t[0:3, 0:3] = r
        t[0:3, 3] = [x, y, z]
        
        return t
