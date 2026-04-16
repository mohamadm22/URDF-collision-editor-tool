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

    def load_mesh(self, file_path: str) -> None:
        """Load and display an STL mesh, clearing prior mesh."""
        self._clear_mesh()
        try:
            mesh = pv.read(file_path)
            mesh = mesh.clean()
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
            self.plotter.reset_camera()
        except Exception as e:
            print(f"[SceneManager] Failed to load mesh: {e}")

    def _clear_mesh(self):
        try:
            self.plotter.remove_actor(_MESH_ACTOR_KEY, render=False)
        except Exception:
            pass
        self._mesh_actor = None

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
        """Forcefully remove any actor in the plotter that starts with 'shape_'."""
        # We scan the plotter's internal registry to ensure nothing is missed
        for name in list(self.plotter.actors.keys()):
            if name.startswith("shape_"):
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
