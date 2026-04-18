"""
ExportController — generates URDF .txt snippets and .json project files.
"""

from __future__ import annotations
import json
import os
from models.project_state import ProjectState
from utils.urdf_modifier import generate_collision_urdf


class ExportController:
    def __init__(self, state: ProjectState):
        self.state = state

    # ------------------------------------------------------------------ #
    # URDF txt export                                                      #
    # ------------------------------------------------------------------ #

    def export_txt(self, output_path: str) -> None:
        """Write URDF <collision> snippets for all meshes to a .txt file."""
        lines = []
        for mesh in self.state.meshes:
            lines.append(f"<!-- {mesh.name} -->")
            if not mesh.shapes:
                lines.append("<!-- No collision shapes defined -->")
            else:
                for shape in mesh.shapes:
                    lines.append(shape.to_urdf_collision())
            lines.append("")   # blank line between files

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    # ------------------------------------------------------------------ #
    # JSON project save / load                                            #
    # ------------------------------------------------------------------ #

    def save_project(self, output_path: str) -> None:
        """Serialise the full project to JSON."""
        data = self.state.to_dict()
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        self.state.project_path = output_path

    def load_project(self, input_path: str) -> ProjectState:
        """Load a project from JSON and return a new ProjectState."""
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        new_state = ProjectState.from_dict(data)
        new_state.project_path = input_path
        return new_state

    # ------------------------------------------------------------------ #
    # Convenience: export both formats at once                            #
    # ------------------------------------------------------------------ #

    def export_all(self, directory: str, base_name: str = "collision_output") -> tuple:
        """Export .txt and .json to the given directory. Returns (txt_path, json_path, urdf_path)."""
        os.makedirs(directory, exist_ok=True)
        txt_path = os.path.join(directory, f"{base_name}.txt")
        json_path = os.path.join(directory, f"{base_name}.json")
        self.export_txt(txt_path)
        self.save_project(json_path)
        
        urdf_out = None
        if self.state.urdf_path and os.path.exists(self.state.urdf_path):
            urdf_name = os.path.basename(self.state.urdf_path).replace(".urdf", "_with_collision.urdf")
            urdf_out = os.path.join(directory, urdf_name)
            self.export_full_urdf_with_collision(urdf_out)
            
        return txt_path, json_path, urdf_out

    def export_full_urdf_with_collision(self, output_path: str) -> str:
        """Generates a new URDF with injected collision elements."""
        if not self.state.urdf_path:
            return ""
        return generate_collision_urdf(
            self.state.urdf_path,
            self.state.meshes,
            output_path
        )
