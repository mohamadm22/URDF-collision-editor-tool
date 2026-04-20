"""
SceneManager — owns the PyVista plotter and coordinates mesh + shape rendering.
"""

from __future__ import annotations
import pyvista as pv
import numpy as np
from typing import Optional


_MESH_ACTOR_KEY = "__stl_mesh__"
_AXES_ACTOR_KEY = "__axes__"


class SceneManager:
    """Manages a pyvista.Plotter instance embedded in Qt."""

    def __init__(self, plotter):
        self.plotter = plotter
        self._shape_actors: dict = {}   # shape_id -> actor
        self._mesh_actor = None
        self._axes_visible = True
        self._current_file_path: Optional[str] = None
        self._current_cache_key: Optional[tuple] = None

        self._configure_plotter()

    # ------------------------------------------------------------------ #
    # Plotter setup                                                        #
    # ------------------------------------------------------------------ #

    def _configure_plotter(self):
        self.plotter.set_background("#1a1a2e")   # dark navy
        self.plotter.add_axes(line_width=3)

    # ------------------------------------------------------------------ #
    # STL Mesh                                                             #
    # ------------------------------------------------------------------ #

    def load_mesh(self, file_path: str, scale: list[float] = [1.0, 1.0, 1.0], orientation_rpy: list[float] = [0.0, 0.0, 0.0]) -> None:
        """Load and display an STL mesh, clearing prior mesh."""
        # Use scale and orientation in cache key
        cache_key = (file_path, tuple(scale), tuple(orientation_rpy))
        if self._current_cache_key == cache_key:
            return

        self._clear_mesh()
        try:
            mesh = pv.read(file_path)
            mesh = mesh.clean()
            
            # Application of URDF orientation (rotation) if requested
            if any(r != 0 for r in orientation_rpy):
                # Build rotation transform (Extrinsic XYZ / Intrinsic ZYX convention)
                r, p, y = orientation_rpy
                # PyVista's transform expects degrees if using rotate_x etc, 
                # but we can build a 4x4 matrix from radians.
                import math
                cos_r, sin_r = math.cos(r), math.sin(r)
                cos_p, sin_p = math.cos(p), math.sin(p)
                cos_y, sin_y = math.cos(y), math.sin(y)
                
                Rx = np.array([[1,0,0],[0,cos_r,-sin_r],[0,sin_r,cos_r]])
                Ry = np.array([[cos_p,0,sin_p],[0,1,0],[-sin_p,0,cos_p]])
                Rz = np.array([[cos_y,-sin_y,0],[sin_y,cos_y,0],[0,0,1]])
                R = Rz @ Ry @ Rx # URDF convention
                
                T = np.eye(4)
                T[:3, :3] = R
                mesh.transform(T, inplace=True)

            # REMOVED: Automatic URDF scaling for display. 
            # We now show the mesh at normalized scale 1.0.
                
            mesh.compute_normals(inplace=True)
            self._mesh_actor = self.plotter.add_mesh(
                mesh,
                color="#c0c8d8",
                opacity=1.0,
                show_edges=False,
                smooth_shading=True,
                name=_MESH_ACTOR_KEY,
                lighting=True,
            )
            self._current_cache_key = cache_key
            self._current_file_path = file_path
            self.plotter.reset_camera()
        except Exception as e:
            print(f"[SceneManager] Failed to load mesh: {e}")
            self._current_cache_key = None
            self._current_file_path = None

    def _clear_mesh(self):
        try:
            self.plotter.remove_actor(_MESH_ACTOR_KEY, render=False)
        except Exception:
            pass
        self._mesh_actor = None
        self._current_file_path = None

    # ------------------------------------------------------------------ #
    # Collision Shapes                                                     #
    # ------------------------------------------------------------------ #

    def update_shapes(self, shapes: list, selected_id: Optional[str] = None) -> None:
        """Re-render all shapes. Highlight the selected one."""
        self._clear_shapes()
        for shape in shapes:
            try:
                mesh = shape.to_pyvista_mesh()
                is_selected = shape.id == selected_id
                r, g, b, a = shape.color
                color = (r, g, b)
                opacity = 0.75 if is_selected else 0.40
                actor = self.plotter.add_mesh(
                    mesh,
                    color=color,
                    opacity=opacity,
                    style="surface",
                    show_edges=is_selected,
                    edge_color="white",
                    name=f"shape_{shape.id}",
                )
                self._shape_actors[shape.id] = actor
            except Exception as e:
                print(f"[SceneManager] Failed to render shape {shape.name}: {e}")
        self.plotter.render()

    def _clear_shapes(self):
        """Remove all shape actors from the plotter."""
        for shape_id in list(self._shape_actors.keys()):
            name = f"shape_{shape_id}"
            try:
                self.plotter.remove_actor(name, render=False)
            except Exception:
                pass
        self._shape_actors.clear()

    def clear_all(self):
        self._clear_mesh()
        self._clear_shapes()
        self.plotter.render()

    # ------------------------------------------------------------------ #
    # Camera / helpers                                                     #
    # ------------------------------------------------------------------ #

    def reset_camera(self):
        self.plotter.reset_camera()
        self.plotter.render()

    def toggle_axes(self, visible: bool):
        self._axes_visible = visible
        # pyvistaqt keeps axes widget persistently; toggle via opacity
        self.plotter.render()
