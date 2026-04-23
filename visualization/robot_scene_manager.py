import os
import pyvista as pv
import numpy as np
import vtk
from typing import Optional, Dict, List, Set
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from models.robot_model import RobotModel, RobotVisualOrigin, RobotLinkVisual
from models.collision_mapping import CollisionOverlayData, LinkCollisionData
from models.shapes.box_shape import BoxShape
from models.shapes.cylinder_shape import CylinderShape
from models.shapes.sphere_shape import SphereShape
from models.shapes.stl_shape import StlShape

class RobotSceneManager(QObject):
    """Manages robot visualization in a dedicated plotter."""
    link_single_clicked = pyqtSignal(str)   # link_name
    link_double_clicked = pyqtSignal(str)   # link_name

    def __init__(self, plotter):
        super().__init__()
        self.plotter = plotter
        # Layered actor storage
        self._visual_actors: Dict[str, pv.Actor] = {}
        self._collision_actors: Dict[str, pv.Actor] = {}
        self._actor_to_link: Dict[int, str] = {} # id(actor) -> link_name
        
        # Mesh cache to prevent redundant disk I/O
        self._mesh_cache: Dict[str, pv.PolyData] = {}
        
        # Visibility state
        self._visual_visible: bool = True
        self._collision_visible: bool = True
        
        # Collision detection state
        self._colliding_links: Set[str] = set()
        
        # Picking / Click state
        self._highlighted_link: str | None = None
        self._pending_pick_link: str | None = None
        self._click_timer = QTimer()
        self._click_timer.setSingleShot(True)
        self._click_timer.setInterval(220) # ms double-click window
        self._click_timer.timeout.connect(self._fire_single_click)
        
        self._configure_plotter()

    def _configure_plotter(self):
        self.plotter.set_background("#111b27")
        self.plotter.add_axes(line_width=2)

    def render_robot(self, model: RobotModel, global_transforms: Dict[str, np.ndarray]) -> None:
        """Updates robot visual meshes using global transforms. Reuses actors where possible."""
        # For now, we still clear and redraw for simplicity, but we optimize mesh usage
        self.clear_visual_layer()
        
        for link_name, link in model.links.items():
            base_t = global_transforms.get(link_name)
            if base_t is None:
                continue

            for i, visual in enumerate(link.visuals):
                try:
                    # Get mesh from cache or load it
                    cached_mesh = self._create_visual_mesh(visual)
                    if cached_mesh is None: continue
                    
                    # IMPORTANT: Build a NEW mesh instance with the transform applied
                    # Do NOT use inplace=True on cached meshes!
                    origin_t = self._build_transform_matrix(visual.origin)
                    final_t = base_t @ origin_t
                    
                    # Create a transformed copy
                    transformed_mesh = cached_mesh.transform(final_t, inplace=False)
                    
                    actor_id = f"vis__{link_name}__{i}"
                    actor = self.plotter.add_mesh(
                        transformed_mesh,
                        color="#a0b0c0",
                        opacity=0.8,
                        name=actor_id,
                        smooth_shading=True,
                        lighting=True,
                        render=False
                    )
                    actor.SetVisibility(self._visual_visible)
                    self._visual_actors[actor_id] = actor
                    self._actor_to_link[id(actor)] = link_name
                    
                except Exception as e:
                    pass # Quietly skip failed visuals to avoid log flooding
        
        # Only render once at the end
        self.plotter.render()

    def render_collision_layer(self, overlay: CollisionOverlayData) -> None:
        """Renders collision shapes on top of the robot with URDF-correct scaling."""
        self.clear_collision_layer()
        
        for link_name, data in overlay.link_collisions.items():
            base_t = overlay.global_transforms.get(link_name)
            if base_t is None:
                continue

            for i, shape in enumerate(data.shapes):
                try:
                    # 1. Create raw mesh from shape
                    raw_mesh = self._create_collision_primitive_mesh(shape, data.mesh_urdf_scale)
                    if raw_mesh is None or raw_mesh.n_points == 0:
                        continue

                    # 2. Compute URDF-space transform chain (Section 8 of Plan)
                    # Position = (shape.pos * visual_scale) + visual_origin
                    sx, sy, sz = data.mesh_urdf_scale
                    vx, vy, vz = data.mesh_urdf_origin_xyz
                    
                    urdf_pos = [
                        shape.position[0] * sx + vx,
                        shape.position[1] * sy + vy,
                        shape.position[2] * sz + vz
                    ]
                    
                    # Compute rotation matrix
                    r_rad = shape.orientation_rad
                    cr, sr = np.cos(r_rad[0]), np.sin(r_rad[0])
                    cp, sp = np.cos(r_rad[1]), np.sin(r_rad[1])
                    cy, sy_rad = np.cos(r_rad[2]), np.sin(r_rad[2])
                    
                    Rx = np.array([[1,0,0],[0,cr,-sr],[0,sr,cr]])
                    Ry = np.array([[cp,0,sp],[0,1,0],[-sp,0,cp]])
                    Rz = np.array([[cy,-sy_rad,0],[sy_rad,cy,0],[0,0,1]])
                    R = Rz @ Ry @ Rx
                    
                    local_T = np.eye(4)
                    local_T[:3, :3] = R
                    local_T[:3, 3] = urdf_pos
                    
                    # 3. Apply global transform
                    final_T = base_t @ local_T
                    raw_mesh.transform(final_T, inplace=True)
                    
                    # 4. Add to plotter
                    actor_id = f"coll__{link_name}__{shape.id}"
                    
                    # Color based on collision state
                    is_colliding = link_name in self._colliding_links
                    color = "#ff2222" if is_colliding else "#00cc55"
                    opacity = 0.55 if is_colliding else 0.35
                    
                    actor = self.plotter.add_mesh(
                        raw_mesh,
                        color=color,
                        opacity=opacity,
                        name=actor_id,
                        render=False
                    )
                    actor.SetVisibility(self._collision_visible)
                    self._collision_actors[actor_id] = actor
                    
                except Exception as e:
                    pass
        self.plotter.render()

    def _create_visual_mesh(self, visual: RobotLinkVisual) -> Optional[pv.PolyData]:
        """Creates a PyVista mesh for the given visual entry."""
        if visual.type == "mesh":
            if not visual.mesh_path or not os.path.exists(visual.mesh_path):
                return None
            
            # Use cache if available
            if visual.mesh_path in self._mesh_cache:
                mesh = self._mesh_cache[visual.mesh_path].copy()
            else:
                mesh = pv.read(visual.mesh_path)
                self._mesh_cache[visual.mesh_path] = mesh.copy()

            if any(s != 1.0 for s in visual.scale):
                mesh.scale(visual.scale, inplace=True)
            return mesh
            
        elif visual.type == "box":
            # size is [x, y, z]
            return pv.Box(bounds=(
                -visual.size[0]/2, visual.size[0]/2,
                -visual.size[1]/2, visual.size[1]/2,
                -visual.size[2]/2, visual.size[2]/2
            ))
            
        elif visual.type == "sphere":
            return pv.Sphere(radius=visual.radius)
            
        elif visual.type == "cylinder":
            # cylinder in PV is along Z by default if given height
            return pv.Cylinder(radius=visual.radius, height=visual.length, direction=(0, 0, 1))
            
        return None

    def _create_collision_primitive_mesh(self, shape: object, visual_scale: List[float]) -> Optional[pv.PolyData]:
        """Creates a PyVista mesh for a collision shape in URDF-scaled space."""
        import copy
        # We need to scale the geometry dimensions exactly like urdf_modifier export does
        sx, sy, sz = visual_scale
        
        if isinstance(shape, BoxShape):
            return pv.Box(bounds=(
                -shape.size_x * sx / 2, shape.size_x * sx / 2,
                -shape.size_y * sy / 2, shape.size_y * sy / 2,
                -shape.size_z * sz / 2, shape.size_z * sz / 2,
            ))
        elif isinstance(shape, CylinderShape):
            return pv.Cylinder(
                radius=shape.radius * max(sx, sy),
                height=shape.length * sz,
                direction=(0, 0, 1)
            )
        elif isinstance(shape, SphereShape):
            return pv.Sphere(radius=shape.radius * max(visual_scale))
        elif isinstance(shape, StlShape):
            # Use cache for STL collision shapes
            if shape.stl_path in self._mesh_cache:
                mesh = self._mesh_cache[shape.stl_path].copy()
                # Apply user scale if not already correct (usually it matches what's in cache if not changed)
                # But to be safe, we apply the shape's scale
                if any(s != 1.0 for s in shape.scale):
                    mesh.scale(shape.scale, inplace=True)
            else:
                mesh = shape._create_raw_mesh()
                # Cache the raw read if appropriate (optional, but shape._create_raw_mesh already reads)
                pass
            
            # Now apply the additional visual_scale (URDF scale)
            if any(s != 1.0 for s in visual_scale):
                mesh.scale(visual_scale, inplace=True)
            return mesh

        return None

    def set_visual_visible(self, visible: bool):
        self._visual_visible = visible
        for actor in self._visual_actors.values():
            actor.SetVisibility(visible)
        self.plotter.render()

    def set_collision_visible(self, visible: bool):
        self._collision_visible = visible
        for actor in self._collision_actors.values():
            actor.SetVisibility(visible)
        self.plotter.render()

    def clear_visual_layer(self):
        self._click_timer.stop()
        self._pending_pick_link = None
        for actor_id in list(self._visual_actors.keys()):
            try: self.plotter.remove_actor(actor_id, render=False)
            except Exception: pass
        self._visual_actors.clear()
        self._actor_to_link.clear()

    def clear_collision_layer(self):
        for actor_id in list(self._collision_actors.keys()):
            try: self.plotter.remove_actor(actor_id, render=False)
            except Exception: pass
        self._collision_actors.clear()

    def clear_robot(self):
        self.clear_visual_layer()
        self.clear_collision_layer()
        self.plotter.render()

    def highlight_collisions(self, colliding_links: Set[str]):
        """Recolors actors for links participating in collisions."""
        prev = self._colliding_links
        self._colliding_links = colliding_links
        
        # Determine which links changed state to minimize updates
        changed = prev.symmetric_difference(colliding_links)
        
        for actor_id, actor in self._collision_actors.items():
            # actor_id is "coll__link_name__shape_id"
            parts = actor_id.split("__")
            if len(parts) < 3: continue
            
            link_name = parts[1]
            if link_name not in changed:
                continue
            
            is_colliding = link_name in colliding_links
            color = "#ff2222" if is_colliding else "#00cc55"
            opacity = 0.55 if is_colliding else 0.35
            
            actor.GetProperty().SetColor(pv.Color(color).float_rgb)
            actor.GetProperty().SetOpacity(opacity)
            
        self.plotter.render()

    def get_collision_meshes(self) -> Dict[str, List[pv.PolyData]]:
        """Returns all currently rendered collision meshes grouped by link name."""
        meshes = {}
        for actor_id, actor in self._collision_actors.items():
            parts = actor_id.split("__")
            if len(parts) < 3: continue
            
            link_name = parts[1]
            if link_name not in meshes:
                meshes[link_name] = []
            
            # Access the underlying mesh from the actor
            meshes[link_name].append(actor.GetMapper().GetInput())
            
        return meshes

    def reset_camera(self):
        self.plotter.reset_camera()
        self.plotter.render()

    # ── Picking System ────────────────────────────────────────────────

    def enable_picking(self):
        """Initializes mesh picking on the robot plotter."""
        self.plotter.enable_mesh_picking(
            self._on_pick_callback,
            use_actor=True,
            show=False, # We handle our own highlights
            left_clicking=True
        )
        # Separate observer to handle background clicks (misses)
        self.plotter.iren.add_observer("LeftButtonPressEvent", self._on_left_click_check)

    def _on_left_click_check(self, obj, event):
        """Checks if a background click occurred to clear highlight."""
        pos = self.plotter.mouse_position
        picker = vtk.vtkPropPicker()
        picker.Pick(pos[0], pos[1], 0, self.plotter.renderer)
        if picker.GetActor() is None:
            self.highlight_link(None)

    def _on_pick_callback(self, actor: Optional[pv.Actor]):
        """Internal callback for VTK picking events."""
        link_name = self._actor_to_link.get(id(actor))
        
        if link_name is None:
            # Clicked empty space or non-visual actor
            self._click_timer.stop()
            self._pending_pick_link = None
            return

        if self._click_timer.isActive() and self._pending_pick_link == link_name:
            # Second click on same link within window -> DOUBLE CLICK
            self._click_timer.stop()
            self._pending_pick_link = None
            self.link_double_clicked.emit(link_name)
        else:
            # First click -> start timer for SINGLE CLICK
            self._click_timer.stop()
            self._pending_pick_link = link_name
            self._click_timer.start()

    def _fire_single_click(self):
        """Called when double-click timer expires."""
        if self._pending_pick_link:
            self.link_single_clicked.emit(self._pending_pick_link)
        self._pending_pick_link = None

    # ── Selection Feedback & Focus ───────────────────────────────────

    def highlight_link(self, link_name: str | None):
        """Visually distinguishes the selected link."""
        self._highlighted_link = link_name
        
        # Batch updates to actor properties
        for actor_id, actor in self._visual_actors.items():
            # actor_id is "vis__link_name__i"
            parts = actor_id.split("__")
            if len(parts) < 2: continue
            
            l_name = parts[1]
            if l_name == link_name:
                actor.GetProperty().SetColor(pv.Color("#ffd966").float_rgb) # Gold
                actor.GetProperty().SetOpacity(1.0)
            else:
                actor.GetProperty().SetColor(pv.Color("#a0b0c0").float_rgb) # Default
                actor.GetProperty().SetOpacity(0.8)
        
        self.plotter.render()

    def focus_camera_on_link(self, link_name: str):
        """Zooms camera to fit all visual actors of the specified link."""
        target_actors = []
        for actor_id, actor in self._visual_actors.items():
            if actor_id.startswith(f"vis__{link_name}__"):
                target_actors.append(actor)
        
        if not target_actors:
            self.reset_camera()
            return

        # Compute union bounding box
        total_bounds = [float('inf'), float('-inf'), float('inf'), float('-inf'), float('inf'), float('-inf')]
        for actor in target_actors:
            b = actor.GetBounds() # xmin, xmax, ymin, ymax, zmin, zmax
            total_bounds[0] = min(total_bounds[0], b[0])
            total_bounds[1] = max(total_bounds[1], b[1])
            total_bounds[2] = min(total_bounds[2], b[2])
            total_bounds[3] = max(total_bounds[3], b[3])
            total_bounds[4] = min(total_bounds[4], b[4])
            total_bounds[5] = max(total_bounds[5], b[5])
        
        # Compute center and radius
        center = [
            (total_bounds[0] + total_bounds[1]) / 2,
            (total_bounds[2] + total_bounds[3]) / 2,
            (total_bounds[4] + total_bounds[5]) / 2
        ]
        dx, dy, dz = (total_bounds[1]-total_bounds[0]), (total_bounds[3]-total_bounds[2]), (total_bounds[5]-total_bounds[4])
        radius = max(dx, dy, dz) / 2
        
        if radius <= 0:
            self.reset_camera()
            return

        # Position camera at an offset
        self.plotter.camera.focal_point = center
        self.plotter.camera.position = [
            center[0],
            center[1] - radius * 3.5, # Pull back
            center[2] + radius * 1.5  # Slight elevation
        ]
        self.plotter.camera.up = (0, 0, 1)
        self.plotter.camera.reset_clipping_range()
        self.plotter.render()

    def _build_transform_matrix(self, origin: RobotVisualOrigin) -> np.ndarray:
        """Builds a 4x4 homogeneous transform matrix from URDF origin."""
        x, y, z = origin.xyz
        roll, pitch, yaw = origin.rpy
        
        # Rotation matrices
        rx = np.array([
            [1, 0, 0],
            [0, np.cos(roll), -np.sin(roll)],
            [0, np.sin(roll), np.cos(roll)]
        ])
        
        ry = np.array([
            [np.cos(pitch), 0, np.sin(pitch)],
            [0, 1, 0],
            [-np.sin(pitch), 0, np.cos(pitch)]
        ])
        
        rz = np.array([
            [np.cos(yaw), -np.sin(yaw), 0],
            [np.sin(yaw), np.cos(yaw), 0],
            [0, 0, 1]
        ])
        
        # URDF order: Rz * Ry * Rx
        r = rz @ ry @ rx
        
        # Homogeneous matrix
        t = np.eye(4)
        t[0:3, 0:3] = r
        t[0:3, 3] = [x, y, z]
        
        return t
