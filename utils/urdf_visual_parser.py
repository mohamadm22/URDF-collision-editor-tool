import os
from lxml import etree
from typing import List, Optional
from models.robot_model import (
    RobotModel, RobotLinkModel, RobotLinkVisual, RobotVisualOrigin, RobotJointModel
)

def parse_urdf_visuals(urdf_path: str, package_root: Optional[str] = None) -> RobotModel:
    """
    Parses URDF for visual elements, primitives, and joints.
    """
    if not os.path.exists(urdf_path):
        raise FileNotFoundError(f"URDF file not found: {urdf_path}")

    urdf_path = os.path.abspath(urdf_path)
    urdf_dir = os.path.dirname(urdf_path)
    
    inferred_pkg_path = None
    if os.path.basename(urdf_dir) == "urdf":
        inferred_pkg_path = os.path.dirname(urdf_dir)

    robot_model = RobotModel(urdf_path=urdf_path, package_root=package_root)
    
    try:
        parser = etree.XMLParser(remove_blank_text=False)
        tree = etree.parse(urdf_path, parser)
        root = tree.getroot()
    except Exception as e:
        raise ValueError(f"Invalid URDF XML: {e}")

    # 1. Process links
    for link_tag in root.xpath("//link"):
        link_name = link_tag.get("name", "unnamed_link")
        link_model = RobotLinkModel(name=link_name)
        
        # Process visual children
        visual_tags = link_tag.xpath("./visual")
        for visual_tag in visual_tags:
            origin = _parse_origin(visual_tag, link_name, robot_model)
            
            # Geometry
            geom_tag = visual_tag.xpath("./geometry")[0] if visual_tag.xpath("./geometry") else None
            if geom_tag is None:
                continue

            # Mesh
            mesh_tags = geom_tag.xpath("./mesh")
            if mesh_tags:
                mesh_tag = mesh_tags[0]
                raw_path = mesh_tag.get("filename")
                if not raw_path:
                    robot_model.load_warnings.append(f"Link '{link_name}': Mesh visual missing filename")
                    continue

                scale_str = mesh_tag.get("scale", "1 1 1")
                try:
                    scale = [float(s) for s in scale_str.split()]
                except ValueError:
                    scale = [1.0, 1.0, 1.0]

                resolved_path = _resolve_visual_path(raw_path, urdf_dir, package_root, inferred_pkg_path)
                if not resolved_path or not os.path.exists(resolved_path):
                    robot_model.load_warnings.append(f"Link '{link_name}': Missing mesh file '{raw_path}'")
                    resolved_path = None

                link_model.visuals.append(RobotLinkVisual(
                    type="mesh",
                    mesh_path=resolved_path,
                    origin=origin,
                    scale=scale,
                    mesh_filename=os.path.basename(raw_path)
                ))
                continue

            # Box
            box_tags = geom_tag.xpath("./box")
            if box_tags:
                size_str = box_tags[0].get("size", "0 0 0")
                try:
                    size = [float(s) for s in size_str.split()]
                except ValueError:
                    size = [0, 0, 0]
                link_model.visuals.append(RobotLinkVisual(type="box", size=size, origin=origin))
                continue

            # Sphere
            sphere_tags = geom_tag.xpath("./sphere")
            if sphere_tags:
                radius = float(sphere_tags[0].get("radius", "0"))
                link_model.visuals.append(RobotLinkVisual(type="sphere", radius=radius, origin=origin))
                continue

            # Cylinder
            cylinder_tags = geom_tag.xpath("./cylinder")
            if cylinder_tags:
                radius = float(cylinder_tags[0].get("radius", "0"))
                length = float(cylinder_tags[0].get("length", "0"))
                link_model.visuals.append(RobotLinkVisual(type="cylinder", radius=radius, length=length, origin=origin))
                continue

        robot_model.links[link_name] = link_model

    # 2. Process joints
    for joint_tag in root.xpath("//joint"):
        joint_name = joint_tag.get("name", "unnamed_joint")
        parent = joint_tag.xpath("./parent")[0].get("link") if joint_tag.xpath("./parent") else None
        child = joint_tag.xpath("./child")[0].get("link") if joint_tag.xpath("./child") else None
        joint_type = joint_tag.get("type", "fixed")
        
        if not parent or not child:
            continue
            
        origin = _parse_origin(joint_tag, joint_name, robot_model)
        robot_model.joints.append(RobotJointModel(
            name=joint_name,
            parent=parent,
            child=child,
            origin=origin,
            type=joint_type
        ))

    return robot_model

def _parse_origin(tag, owner_name: str, model: RobotModel) -> RobotVisualOrigin:
    origin_tag = tag.xpath("./origin")
    origin = RobotVisualOrigin()
    if len(origin_tag) > 0:
        xyz_str = origin_tag[0].get("xyz", "0 0 0")
        rpy_str = origin_tag[0].get("rpy", "0 0 0")
        try:
            origin.xyz = [float(s) for s in xyz_str.split()]
            origin.rpy = [float(s) for s in rpy_str.split()]
        except ValueError:
            model.load_warnings.append(f"'{owner_name}': Malformed origin xyz='{xyz_str}' rpy='{rpy_str}'")
    return origin

def _resolve_visual_path(raw_path: str, urdf_dir: str, package_root: Optional[str] = None, inferred_root: Optional[str] = None) -> Optional[str]:
    """Helper to resolve visual mesh paths."""
    resolved_path = None
    
    if raw_path.startswith("package://"):
        # 1. User provided package root
        if package_root:
            stripped = raw_path[len("package://"):]
            resolved_path = os.path.normpath(os.path.join(package_root, stripped))
            
        # 2. Inferred root from /urdf sibling folder structure
        if (not resolved_path or not os.path.exists(resolved_path)) and inferred_root:
            parts = raw_path[len("package://"):].split("/", 1)
            if len(parts) > 1:
                inner_path = parts[1] # e.g. "meshes/base_link.stl"
                test_path = os.path.normpath(os.path.join(inferred_root, inner_path))
                if os.path.exists(test_path):
                    resolved_path = test_path
                else:
                    # Alternative common structure: try /meshes/<filename>
                    test_meshes_path = os.path.normpath(os.path.join(inferred_root, "meshes", os.path.basename(raw_path)))
                    if os.path.exists(test_meshes_path):
                        resolved_path = test_meshes_path
    else:
        # Absolute or Relative
        if os.path.isabs(raw_path):
            resolved_path = raw_path
        else:
            resolved_path = os.path.normpath(os.path.join(urdf_dir, raw_path))
            
    return resolved_path
