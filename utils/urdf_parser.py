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

        # Resolution Strategy
        resolved_path = None
        
        if raw_path.startswith("package://"):
            # 1. Try with user-provided package_root
            if package_root:
                resolved_path = _resolve_package_path(raw_path, package_root)
            
            # 2. Heuristic: If URDF is in a standard /urdf folder, try the sibling /meshes folder
            if not resolved_path or not os.path.exists(resolved_path):
                if inferred_pkg_path:
                    # Strip package://pkg_name/ and just look in inferred/meshes/ or similar?
                    # ROS standard: package://pkg_name/meshes/file.stl
                    # Let's try joining inferred_pkg_path with the part after the package name
                    parts = raw_path[len("package://"):].split("/", 1)
                    if len(parts) > 1:
                        inner_path = parts[1] # e.g. "meshes/mid_stomach.stl"
                        # 1. Try joining with inner path (standard)
                        test_path = os.path.normpath(os.path.join(inferred_pkg_path, inner_path))
                        if os.path.exists(test_path):
                            resolved_path = test_path
                        else:
                            # 2. Try specifically in <pkg>/meshes/<filename> as requested
                            test_meshes_path = os.path.normpath(os.path.join(inferred_pkg_path, "meshes", os.path.basename(raw_path)))
                            if os.path.exists(test_meshes_path):
                                resolved_path = test_meshes_path

        else:
            # Absolute or Relative
            if os.path.isabs(raw_path):
                resolved_path = raw_path
            else:
                resolved_path = os.path.normpath(os.path.join(urdf_dir, raw_path))

        results.append({
            "raw_path": raw_path,
            "resolved_path": resolved_path,
            "scale": scale,
            "filename": os.path.basename(raw_path),
            "is_resolved": resolved_path is not None and os.path.exists(resolved_path)
        })

    return results

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
