"""
ShapeController — manages CRUD operations on shapes for the current mesh.
Each mutating operation saves an undo snapshot before modifying state.
"""

from __future__ import annotations
from models.project_state import ProjectState
from models.shapes import CylinderShape, BoxShape, SphereShape, SHAPE_REGISTRY

_SHAPE_DEFAULTS = {
    "CylinderShape": CylinderShape,
    "BoxShape": BoxShape,
    "SphereShape": SphereShape,
}


class ShapeController:
    def __init__(self, state: ProjectState):
        self.state = state

    # ------------------------------------------------------------------ #
    # Add                                                                  #
    # ------------------------------------------------------------------ #

    def add_shape(self, shape_type: str) -> str | None:
        """Create a default shape of the given type and add it to the current mesh.
        Returns the new shape's id, or None if mesh is invalid."""
        mesh = self.state.current_mesh
        if mesh is None:
            return None
        klass = _SHAPE_DEFAULTS.get(shape_type)
        if klass is None:
            return None

        self.state.push_undo()
        shape = klass()
        # Auto-name: e.g. "Cylinder_2"
        count = sum(1 for s in mesh.shapes if type(s).__name__ == shape_type) + 1
        shape.name = f"{shape.name}_{count}"
        mesh.add_shape(shape)
        return shape.id

    # ------------------------------------------------------------------ #
    # Remove                                                               #
    # ------------------------------------------------------------------ #

    def remove_shape(self, shape_id: str) -> None:
        mesh = self.state.current_mesh
        if mesh is None:
            return
        self.state.push_undo()
        mesh.remove_shape(shape_id)

    # ------------------------------------------------------------------ #
    # Update                                                               #
    # ------------------------------------------------------------------ #

    def update_shape(self, shape_id: str, params: dict) -> bool:
        """Update shape parameters from a flat params dict.
        Recognised keys: position, orientation_deg, name, and shape-specific
        fields (radius, length, size_x, size_y, size_z).
        Returns True if shape was found and updated."""
        mesh = self.state.current_mesh
        if mesh is None:
            return False
        shape = mesh.get_shape(shape_id)
        if shape is None:
            return False

        self.state.push_undo()
        for key, value in params.items():
            if hasattr(shape, key):
                setattr(shape, key, value)
        return True

    # ------------------------------------------------------------------ #
    # Undo / Redo                                                          #
    # ------------------------------------------------------------------ #

    def undo(self) -> bool:
        return self.state.undo()

    def redo(self) -> bool:
        return self.state.redo()
