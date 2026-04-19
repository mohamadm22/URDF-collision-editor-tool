"""Shape package – registry for all primitive types."""

from models.shapes.cylinder_shape import CylinderShape
from models.shapes.box_shape import BoxShape
from models.shapes.sphere_shape import SphereShape
from models.shapes.stl_shape import StlShape

SHAPE_REGISTRY: dict = {
    "CylinderShape": CylinderShape,
    "BoxShape": BoxShape,
    "SphereShape": SphereShape,
    "StlShape": StlShape,
}

__all__ = ["CylinderShape", "BoxShape", "SphereShape", "StlShape", "SHAPE_REGISTRY"]
