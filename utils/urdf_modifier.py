import os
from lxml import etree
import copy
from typing import List
from models.mesh_model import MeshModel
from models.shapes.box_shape import BoxShape
from models.shapes.cylinder_shape import CylinderShape
from models.shapes.sphere_shape import SphereShape
from models.shapes.stl_shape import StlShape

def generate_collision_urdf(
    original_urdf_path: str,
    meshes: List[MeshModel],
    output_path: str
) -> str:
    """
    Parses original URDF, matches links to meshes, scales shapes, and injects collision elements.
    Saves the result to output_path and returns the path.
    """
    if not os.path.exists(original_urdf_path):
        raise FileNotFoundError(f"Original URDF not found: {original_urdf_path}")

    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.parse(original_urdf_path, parser)
    root = tree.getroot()

    # Build a lookup for MeshModel by filename
    mesh_lookup = {os.path.normpath(m.file_path): m for m in meshes}
    # Also lookup by basename for easier matching
    basename_lookup = {os.path.basename(m.file_path): m for m in meshes}

    def normalize_link_mesh_path(path: str) -> str:
        # Handle package:// prefix by stripping it for matching purposes
        if path.startswith("package://"):
            return os.path.basename(path)
        return os.path.basename(path)

    # Find all links
    for link in root.xpath("//link"):
        visual = link.find("visual")
        if visual is None:
            continue
        
        geom = visual.find("geometry")
        if geom is None:
            continue
        
        mesh_tag = geom.find("mesh")
        if mesh_tag is None:
            continue
            
        filename = mesh_tag.get("filename")
        if not filename:
            continue
            
        # Try to find a match
        matched_mesh = basename_lookup.get(normalize_link_mesh_path(filename))
        if not matched_mesh:
            continue
            
        if not matched_mesh.shapes:
            continue

        # Get scale from visual mesh
        scale_str = mesh_tag.get("scale", "1 1 1")
        try:
            sx, sy, sz = map(float, scale_str.split())
        except ValueError:
            sx, sy, sz = 1.0, 1.0, 1.0

        # Remove existing collision elements IF we are injecting new ones
        for existing_collision in link.xpath("collision"):
            link.remove(existing_collision)

        # Inject new collision elements
        for shape in matched_mesh.shapes:
            # Create a copy so we don't modify the original state
            s = copy.deepcopy(shape)
            
            # Export Rule: Multiply position by original URDF visual scale (sx, sy, sz)
            # This ensures the collision origin remains aligned with the visual mesh in URDF space.
            s.position[0] *= sx
            s.position[1] *= sy
            s.position[2] *= sz
            
            # Additional geometry scaling for primitives
            if isinstance(s, BoxShape):
                s.size_x *= sx
                s.size_y *= sy
                s.size_z *= sz
            elif isinstance(s, CylinderShape):
                # Using max(sx, sy) for radius as a heuristic
                s.radius *= max(sx, sy)
                s.length *= sz
            elif isinstance(s, SphereShape):
                # Using max of all scales for radius
                s.radius *= max(sx, sy, sz)
            # Note: StlShape multiplication (user_scale * urdf_visual_scale)
            # is handled internally by StlShape.to_urdf_geometry().
            
            # Generate XML snippet
            collision_xml_str = s.to_urdf_collision()
            collision_element = etree.fromstring(collision_xml_str)
            link.append(collision_element)

    # Save the new URDF
    tree.write(output_path, pretty_print=True, xml_declaration=True, encoding="utf-8")
    return output_path
