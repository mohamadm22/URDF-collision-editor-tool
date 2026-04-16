"""Shape package – registry for all primitive types."""

from models.shapes.cylinder_shape import CylinderShape
from models.shapes.box_shape import BoxShape
from models.shapes.sphere_shape import SphereShape

SHAPE_REGISTRY: dict = {
    "CylinderShape": CylinderShape,
    "BoxShape": BoxShape,
    "SphereShape": SphereShape,
}

__all__ = ["CylinderShape", "BoxShape", "SphereShape", "SHAPE_REGISTRY"]
