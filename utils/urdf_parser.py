import os
from lxml import etree
from typing import List, Dict, Optional

def extract_meshes_from_urdf(urdf_path: str, package_root: Optional[str] = None) -> List[Dict]:
    """
    Parses URDF and extracts visual mesh file paths and their scales.
    Returns list of dicts: [{"raw_path": ..., "resolved_path": ..., "scale": ..., "filename": ...}]
    """
    if not os.path.exists(urdf_path):
        raise FileNotFoundError(f"URDF file not found: {urdf_path}")

    # Canonicalize paths
    urdf_path = os.path.abspath(urdf_path)
    urdf_dir = os.path.dirname(urdf_path)
    
    # Try to infer package path from common ROS structure: <pkg_root>/urdf/<file>.urdf
    inferred_pkg_path = None
    if os.path.basename(urdf_dir) == "urdf":
        inferred_pkg_path = os.path.dirname(urdf_dir)

    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.parse(urdf_path, parser)
    root = tree.getroot()

    results = []
    # Find all visual mesh tags
    for mesh_tag in root.xpath("//visual//geometry//mesh"):
        raw_path = mesh_tag.get("filename")
        if not raw_path:
            continue

        scale_str = mesh_tag.get("scale", "1 1 1")
        try:
            scale = [float(s) for s in scale_str.split()]
        except ValueError:
            scale = [1.0, 1.0, 1.0]

        resolved_path = _resolve_path(raw_path, urdf_dir, package_root, inferred_pkg_path)

        # Extract visual origin
        visual_tag = mesh_tag.xpath("ancestor::visual")[0]
        origin_tag = visual_tag.find("origin")
        v_xyz = [0.0, 0.0, 0.0]
        v_rpy = [0.0, 0.0, 0.0]
        if origin_tag is not None:
            try:
                v_xyz = [float(s) for s in origin_tag.get("xyz", "0 0 0").split()]
                v_rpy = [float(s) for s in origin_tag.get("rpy", "0 0 0").split()]
            except ValueError:
                pass

        results.append({
            "raw_path": raw_path,
            "resolved_path": resolved_path,
            "scale": scale,
            "origin_xyz": v_xyz,
            "origin_rpy": v_rpy,
            "filename": os.path.basename(raw_path),
            "is_resolved": resolved_path is not None and os.path.exists(resolved_path)
        })

    return results

def extract_collision_shapes_from_urdf(urdf_path: str, package_root: Optional[str] = None) -> Dict[str, List[Dict]]:
    """
    Parses URDF and extracts collision mesh geometries for each link.
    Returns dict: {link_name: [{"raw_path": ..., "resolved_path": ..., "scale": ..., "origin_xyz": ..., "origin_rpy": ..., "is_resolved": ...}]}
    """
    if not os.path.exists(urdf_path):
        raise FileNotFoundError(f"URDF file not found: {urdf_path}")

    urdf_path = os.path.abspath(urdf_path)
    urdf_dir = os.path.dirname(urdf_path)
    
    inferred_pkg_path = None
    if os.path.basename(urdf_dir) == "urdf":
        inferred_pkg_path = os.path.dirname(urdf_dir)

    parser = etree.XMLParser(remove_blank_text=False)
    tree = etree.parse(urdf_path, parser)
    root = tree.getroot()

    link_collisions = {}

    for link in root.xpath("//link"):
        link_name = link.get("name")
        if not link_name:
            continue
            
        shapes = []
        # Find all collision mesh tags in this link
        for collision_tag in link.xpath(".//collision"):
            mesh_tag = collision_tag.find(".//geometry/mesh")
            if mesh_tag is None:
                continue
                
            raw_path = mesh_tag.get("filename")
            if not raw_path:
                continue
                
            scale_str = mesh_tag.get("scale", "1 1 1")
            try:
                scale = [float(s) for s in scale_str.split()]
            except ValueError:
                scale = [1.0, 1.0, 1.0]
                
            origin_tag = collision_tag.find("origin")
            xyz = [0.0, 0.0, 0.0]
            rpy = [0.0, 0.0, 0.0]
            if origin_tag is not None:
                xyz_str = origin_tag.get("xyz", "0 0 0")
                rpy_str = origin_tag.get("rpy", "0 0 0")
                try:
                    xyz = [float(s) for s in xyz_str.split()]
                    rpy = [float(s) for s in rpy_str.split()]
                except ValueError:
                    pass

            resolved_path = _resolve_path(raw_path, urdf_dir, package_root, inferred_pkg_path)

            shapes.append({
                "raw_path": raw_path,
                "resolved_path": resolved_path,
                "scale": scale,
                "origin_xyz": xyz,
                "origin_rpy": rpy,
                "is_resolved": resolved_path is not None and os.path.exists(resolved_path)
            })
            
        if shapes:
            link_collisions[link_name] = shapes

    return link_collisions

def _resolve_path(raw_path: str, urdf_dir: str, package_root: Optional[str], inferred_pkg_path: Optional[str]) -> Optional[str]:
    """Common resolution logic for mesh paths."""
    resolved_path = None
    
    if raw_path.startswith("package://"):
        if package_root:
            resolved_path = _resolve_package_path(raw_path, package_root)
        
        if not resolved_path or not os.path.exists(resolved_path):
            if inferred_pkg_path:
                parts = raw_path[len("package://"):].split("/", 1)
                if len(parts) > 1:
                    inner_path = parts[1]
                    test_path = os.path.normpath(os.path.join(inferred_pkg_path, inner_path))
                    if os.path.exists(test_path):
                        resolved_path = test_path
                    else:
                        test_meshes_path = os.path.normpath(os.path.join(inferred_pkg_path, "meshes", os.path.basename(raw_path)))
                        if os.path.exists(test_meshes_path):
                            resolved_path = test_meshes_path
    else:
        if os.path.isabs(raw_path):
            resolved_path = raw_path
        else:
            resolved_path = os.path.normpath(os.path.join(urdf_dir, raw_path))
            
    return resolved_path

def _resolve_package_path(raw_path: str, root: str) -> str:
    """Helper to join package:// path with a root."""
    # Standard implementation: strip 'package://' and join to root
    stripped = raw_path[len("package://"):]
    return os.path.normpath(os.path.join(root, stripped))

def resolve_mesh_path(raw_path: str, urdf_dir: str, package_root: Optional[str] = None) -> Optional[str]:
    # This is kept for backward compatibility if needed, but extract_meshes_from_urdf is preferred now
    if raw_path.startswith("package://"):
        if package_root:
            return _resolve_package_path(raw_path, package_root)
        return None
    if os.path.isabs(raw_path):
        return raw_path
    return os.path.normpath(os.path.join(urdf_dir, raw_path))
