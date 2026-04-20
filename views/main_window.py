"""
MainWindow — root Qt window; wires all panels, controllers, and the 3D scene.
"""

from __future__ import annotations
import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLabel, QStatusBar, QFileDialog, QMessageBox,
    QProgressDialog, QMenuBar,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt6.QtGui import QAction, QFont, QKeySequence, QShortcut

from pyvistaqt import BackgroundPlotter

from models.project_state import ProjectState
from models.mesh_model import MeshModel
from controllers.file_controller import FileController
from controllers.shape_controller import ShapeController
from controllers.export_controller import ExportController
from visualization.scene_manager import SceneManager
from views.file_panel import FilePanel
from views.shape_list_panel import ShapeListPanel
from views.property_panel import PropertyPanel

from controllers.robot_controller import RobotController
from visualization.robot_scene_manager import RobotSceneManager
from views.robot_viewer_panel import RobotViewerPanel
from pyvistaqt import QtInteractor



# ─────────────────────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    """Root application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("URDF Collision Editor")
        self.resize(1400, 820)
        self.setMinimumSize(900, 600)

        # ── Model ──────────────────────────────────────────────────────
        self._state = ProjectState()

        # ── Controllers ────────────────────────────────────────────────
        self._file_ctrl = FileController(self._state, parent=self)
        self._shape_ctrl = ShapeController(self._state)
        self._export_ctrl = ExportController(self._state)
        self._robot_ctrl = RobotController(parent=self)

        # ── State for selected shape ───────────────────────────────────
        self._selected_shape_id: str | None = None

        # ── Build UI ───────────────────────────────────────────────────
        self._build_menu()
        self._build_central()
        self._build_status_bar()
        self._apply_stylesheet()

        # ── Wire signals ───────────────────────────────────────────────
        self._wire_signals()

        # ── Undo / redo shortcuts ──────────────────────────────────────
        QShortcut(QKeySequence("Ctrl+Z"), self).activated.connect(self._on_undo)
        QShortcut(QKeySequence("Ctrl+Shift+Z"), self).activated.connect(self._on_redo)
        QShortcut(QKeySequence("Ctrl+Y"), self).activated.connect(self._on_redo)

    # ──────────────────────────────────────────────────────────────────
    # Menu bar                                                           #
    # ──────────────────────────────────────────────────────────────────

    def _build_menu(self):
        mb = self.menuBar()
        mb.setNativeMenuBar(False)

        file_menu = mb.addMenu("&File")
        file_menu.addAction(self._action("📂  Open STL Files…", "Ctrl+O", self._on_open_files))
        file_menu.addAction(self._action("➕  Append STL Files…", "Ctrl+Shift+O", self._on_append_files))
        file_menu.addSeparator()
        file_menu.addAction(self._action("💾  Save Project (JSON)…", "Ctrl+S", self._on_save_project))
        file_menu.addAction(self._action("📂  Load Project (JSON)…", "Ctrl+L", self._on_load_project))
        file_menu.addSeparator()
        file_menu.addAction(self._action("❌  Quit", "Ctrl+Q", self.close))

        edit_menu = mb.addMenu("&Edit")
        edit_menu.addAction(self._action("↩  Undo", "Ctrl+Z", self._on_undo))
        edit_menu.addAction(self._action("↪  Redo", "Ctrl+Shift+Z", self._on_redo))

        view_menu = mb.addMenu("&View")
        view_menu.addAction(self._action("🎥  Reset Camera", "R", self._on_reset_camera))
        if hasattr(self, "_robot_panel"):
            view_menu.addAction(self._robot_panel.toggleViewAction())

    def _action(self, label, shortcut, slot) -> QAction:
        a = QAction(label, self)
        if shortcut:
            a.setShortcut(shortcut)
        a.triggered.connect(slot)
        return a

    # ──────────────────────────────────────────────────────────────────
    # Central widget                                                     #
    # ──────────────────────────────────────────────────────────────────

    def _build_central(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Main horizontal splitter ───────────────────────────────────
        h_splitter = QSplitter(Qt.Orientation.Horizontal)
        h_splitter.setHandleWidth(4)

        # Left: file panel
        self._file_panel = FilePanel()
        h_splitter.addWidget(self._file_panel)

        # Centre: vertical splitter (3D + shape list)
        centre_splitter = QSplitter(Qt.Orientation.Vertical)
        centre_splitter.setHandleWidth(4)

        # 3D viewport
        self._plotter = BackgroundPlotter(show=False, off_screen=False)
        self._plotter.setMinimumHeight(300)
        centre_splitter.addWidget(self._plotter)

        # Shape list
        self._shape_list = ShapeListPanel()
        self._shape_list.setMinimumHeight(120)
        self._shape_list.setMaximumHeight(220)
        centre_splitter.addWidget(self._shape_list)
        centre_splitter.setSizes([580, 180])

        h_splitter.addWidget(centre_splitter)

        # Right: property panel
        self._prop_panel = PropertyPanel()
        h_splitter.addWidget(self._prop_panel)

        h_splitter.setSizes([180, 900, 260])
        root.addWidget(h_splitter, 1)

        # ── Robot Viewer Dock ──────────────────────────────────────────
        self._robot_plotter = QtInteractor(self)
        self._robot_panel = RobotViewerPanel(self._robot_plotter)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._robot_panel)
        self._robot_panel.setVisible(False)

        # ── Bottom navigation bar ──────────────────────────────────────
        root.addWidget(self._build_nav_bar())

        # ── Scene managers ─────────────────────────────────────────────
        self._scene = SceneManager(self._plotter)
        self._robot_scene = RobotSceneManager(self._robot_plotter)

    def _build_nav_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(52)
        bar.setStyleSheet("background: #0d1520; border-top: 1px solid #1e2a38;")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 6, 16, 6)

        self._prev_btn = self._nav_button("◀  Previous", self._on_prev)
        self._progress_label = QLabel("")
        self._progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._progress_label.setStyleSheet("color: #88aacc; font-size: 13px;")
        self._next_btn = self._nav_button("Next  ▶", self._on_next)

        lay.addWidget(self._prev_btn)
        lay.addStretch()
        lay.addWidget(self._progress_label)
        lay.addStretch()
        lay.addWidget(self._next_btn)
        return bar

    def _nav_button(self, label: str, slot) -> QPushButton:
        btn = QPushButton(label)
        btn.setFixedHeight(36)
        btn.setMinimumWidth(130)
        btn.setEnabled(False)
        btn.setStyleSheet("""
            QPushButton {
                background: #1a3050; color: #a0d0ff; border: 1px solid #2a5070;
                border-radius: 6px; font-size: 13px; padding: 0 16px;
            }
            QPushButton:hover { background: #254570; }
            QPushButton:disabled { background: #111820; color: #445; border-color: #222; }
        """)
        btn.clicked.connect(slot)
        return btn

    def _build_status_bar(self):
        sb = QStatusBar()
        sb.setStyleSheet("background: #080e16; color: #668; font-size: 11px;")
        self.setStatusBar(sb)
        self._status = sb

    # ──────────────────────────────────────────────────────────────────
    # Signal wiring                                                      #
    # ──────────────────────────────────────────────────────────────────

    def _wire_signals(self):
        # FileController → UI
        self._file_ctrl.mesh_changed.connect(self._on_mesh_changed)

        # FilePanel → navigate
        self._file_panel.file_selected.connect(self._file_ctrl.navigate_to)
        self._file_panel.urdf_selected.connect(self._on_urdf_selected)

        # ShapeListPanel → controllers
        self._shape_list.add_shape_requested.connect(self._on_add_shape)
        self._shape_list.shape_selected.connect(self._on_shape_selected)
        self._shape_list.shape_delete_requested.connect(self._on_delete_shape)

        # PropertyPanel → ShapeController
        self._prop_panel.shape_updated.connect(self._on_shape_params_changed)

        # RobotController signals
        self._robot_ctrl.robot_loaded.connect(self._on_robot_loaded)
        self._robot_ctrl.robot_load_failed.connect(self._on_robot_load_failed)
        self._robot_ctrl.robot_cleared.connect(self._robot_scene.clear_robot)
        self._robot_ctrl.package_root_required.connect(self._on_robot_package_root_required)
        
        # RobotViewerPanel → RobotController
        self._robot_panel.frame_changed.connect(self._robot_ctrl.set_base_frame)

    # ──────────────────────────────────────────────────────────────────
    # File slots                                                         #
    # ──────────────────────────────────────────────────────────────────

    def _on_open_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Open STL Files", "", "STL Files (*.stl);;All Files (*)"
        )
        if paths:
            self._file_ctrl.load_files(paths)

    def _on_append_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Append STL Files", "", "STL Files (*.stl);;All Files (*)"
        )
        if paths:
            self._file_ctrl.append_files(paths)

    def _on_save_project(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Project", "collision_project.json", "JSON (*.json)"
        )
        if path:
            self._export_ctrl.save_project(path)
            self._status.showMessage(f"Project saved → {path}", 5000)

    def _on_load_project(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Load Project", "", "JSON (*.json)"
        )
        if path:
            new_state = self._export_ctrl.load_project(path)
            self._state.meshes = new_state.meshes
            self._state.current_index = new_state.current_index
            self._state.project_path = new_state.project_path
            self._state.urdf_path = new_state.urdf_path
            self._file_panel.set_urdf_path(self._state.urdf_path)
            self._file_ctrl._emit_changed()
            
            # Auto-trigger robot viewer if URDF is linked
            if self._state.urdf_path:
                self._robot_ctrl.load_urdf(self._state.urdf_path)
                
            self._status.showMessage(f"Project loaded ← {path}", 5000)

    # ──────────────────────────────────────────────────────────────────
    # Mesh changed (file navigation)                                     #
    # ──────────────────────────────────────────────────────────────────

    def _on_mesh_changed(self, mesh: MeshModel, index: int, total: int):
        self._selected_shape_id = None

        # Update file panel
        self._file_panel.refresh(self._state.meshes, index)
        self._file_panel.set_urdf_path(self._state.urdf_path)

        # Update progress label
        self._progress_label.setText(f"File {index + 1} / {total}   —   {mesh.name}")

        # Navigation buttons
        self._prev_btn.setEnabled(index > 0)
        is_last = index >= total - 1
        self._next_btn.setEnabled(True)
        self._next_btn.setText("🏁  Finish" if is_last else "Next  ▶")
        self._next_btn.setStyleSheet(
            self._finish_style() if is_last else self._next_style()
        )

        # Load mesh into 3D viewer - Normalized scale 1, but applying URDF rotation
        self._scene.load_mesh(mesh.file_path, scale=[1.0, 1.0, 1.0], orientation_rpy=mesh.urdf_origin_rpy)
        self._scene.update_shapes(mesh.shapes, self._selected_shape_id)

        # Shape list
        self._shape_list.refresh(mesh.shapes)
        self._prop_panel.clear()

        self._status.showMessage(f"Loaded: {mesh.file_path}")

    # ──────────────────────────────────────────────────────────────────
    # Shape slots                                                        #
    # ──────────────────────────────────────────────────────────────────

    def _on_add_shape(self, shape_type: str):
        shape_id = self._shape_ctrl.add_shape(shape_type)
        if shape_id:
            self._refresh_shapes()
            self._shape_list.select_shape_id(shape_id)
            self._on_shape_selected(shape_id)

    def _on_shape_selected(self, shape_id: str):
        self._selected_shape_id = shape_id
        mesh = self._state.current_mesh
        if mesh:
            shape = mesh.get_shape(shape_id)
            self._prop_panel.load_shape(shape)
            self._scene.update_shapes(mesh.shapes, shape_id)

    def _on_delete_shape(self, shape_id: str):
        self._shape_ctrl.remove_shape(shape_id)
        self._selected_shape_id = None
        self._prop_panel.clear()
        self._refresh_shapes()

    def _on_shape_params_changed(self, shape_id: str, params: dict):
        self._shape_ctrl.update_shape(shape_id, params)
        mesh = self._state.current_mesh
        if mesh:
            shape = mesh.get_shape(shape_id)
            # Refresh name in list if it changed
            self._shape_list.refresh(mesh.shapes)
            self._shape_list.select_shape_id(shape_id)
            self._prop_panel.load_shape(shape)
            self._scene.update_shapes(mesh.shapes, shape_id)
        self._file_panel.refresh(self._state.meshes, self._state.current_index)

    def _refresh_shapes(self):
        mesh = self._state.current_mesh
        if mesh:
            self._shape_list.refresh(mesh.shapes)
            self._scene.update_shapes(mesh.shapes, self._selected_shape_id)
        self._file_panel.refresh(self._state.meshes, self._state.current_index)
        self._file_panel.set_urdf_path(self._state.urdf_path)

    def _on_urdf_selected(self, path: str):
        self._state.urdf_path = path
        self._status.showMessage(f"Linked URDF: {path}")
        
        # Trigger Auto-Import
        self._run_urdf_import(path)

    def _run_urdf_import(self, urdf_path: str, pkg_root: str = None):
        res = self._file_ctrl.import_urdf_meshes(urdf_path, pkg_root)
        
        if res.get("error"):
            QMessageBox.critical(self, "URDF Import Error", res["error"])
            return

        if res.get("needs_package_root"):
            QMessageBox.warning(
                self, 
                "Package Root Required",
                "Some meshes with 'package://' paths could not be found automatically in the sibling '/meshes' directory.\n\n"
                "Please select the base directory for the package(s) so the program can find them."
            )
            root = QFileDialog.getExistingDirectory(self, "Select Package Root Directory")
            if root:
                # Retry with root
                self._run_urdf_import(urdf_path, root)
            return

        # Show summary
        added = res.get("added", 0)
        skipped = res.get("skipped_duplicate", 0)
        missing = res.get("missing_file", [])
        
        msg = f"URDF Mesh Import Complete:\n\n"
        msg += f"✅ Added: {added}\n"
        if skipped > 0:
            msg += f"⏭ Skipped (Duplicates): {skipped}\n"
        if missing:
            msg += f"❌ Missing Files: {len(missing)}\n"
            for m in missing[:5]: # Show first 5
                msg += f"   - {os.path.basename(m)}\n"
            if len(missing) > 5:
                msg += "   ... and more\n"
        
        if added > 0 or missing or skipped > 0:
            QMessageBox.information(self, "Import Summary", msg)
            
        # Also trigger Robot Visual Viewer
        self._robot_ctrl.load_urdf(urdf_path)

    def _on_robot_loaded(self, model: RobotModel, transforms: dict):
        self._robot_scene.render_robot(model, transforms)
        self._robot_panel.update_model(model)
        self._robot_panel.setVisible(True)
        
        if model.load_warnings:
            # Maybe don't show all warnings in a popup if too many, but definitely some feedback
            print(f"Robot loaded with {len(model.load_warnings)} warnings")

    def _on_robot_load_failed(self, error: str):
        QMessageBox.critical(self, "Robot Viewer Error", f"Failed to load robot visualization:\n{error}")
        self._robot_panel.setVisible(False)

    def _on_robot_package_root_required(self, urdf_path: str):
        QMessageBox.information(
            self, 
            "Package Root Required for Viewer",
            "The Robot Viewer needs a package root to resolve some visual meshes.\n"
            "Please select the base directory for the package(s)."
        )
        root = QFileDialog.getExistingDirectory(self, "Select Package Root Directory")
        if root:
            self._robot_ctrl.load_urdf(urdf_path, root)

    # ──────────────────────────────────────────────────────────────────
    # Navigation slots                                                   #
    # ──────────────────────────────────────────────────────────────────

    def _on_next(self):
        if self._state.is_last:
            self._on_finish()
        else:
            self._file_ctrl.next_file()

    def _on_prev(self):
        self._file_ctrl.prev_file()

    def _on_finish(self):
        if not self._state.meshes:
            return
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if not directory:
            return
        try:
            txt_p, json_p, urdf_p = self._export_ctrl.export_all(directory)
            
            msg = f"✅ Export successful!\n\n"
            msg += f"URDF snippets → {os.path.basename(txt_p)}\n"
            msg += f"Project file  → {os.path.basename(json_p)}"
            if urdf_p:
                msg += f"\nModified URDF → {os.path.basename(urdf_p)}"
            
            QMessageBox.information(self, "Export Complete", msg)
            self._status.showMessage(f"Exported to {directory}", 8000)
        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Export Error", str(e))

    # ──────────────────────────────────────────────────────────────────
    # Edit slots                                                         #
    # ──────────────────────────────────────────────────────────────────

    def _on_undo(self):
        if self._shape_ctrl.undo():
            self._selected_shape_id = None
            self._prop_panel.clear()
            self._refresh_shapes()
            self._status.showMessage("Undo", 2000)

    def _on_redo(self):
        if self._shape_ctrl.redo():
            self._selected_shape_id = None
            self._prop_panel.clear()
            self._refresh_shapes()
            self._status.showMessage("Redo", 2000)

    def _on_reset_camera(self):
        self._scene.reset_camera()

    # ──────────────────────────────────────────────────────────────────
    # Stylesheet                                                         #
    # ──────────────────────────────────────────────────────────────────

    def _apply_stylesheet(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background: #0d1520;
                color: #c8d8e8;
                font-family: 'Segoe UI', 'Ubuntu', sans-serif;
                font-size: 12px;
            }
            QMenuBar {
                background: #080e16;
                color: #99bbdd;
                border-bottom: 1px solid #1e2a38;
            }
            QMenuBar::item:selected { background: #1a3050; }
            QMenu {
                background: #111928;
                color: #ccd;
                border: 1px solid #2a3a4a;
                border-radius: 4px;
            }
            QMenu::item:selected { background: #1e3d5c; }
            QSplitter::handle { background: #1a2538; }
            QScrollBar:vertical {
                background: #111928; width: 8px; border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #2a4060; border-radius: 4px; min-height: 20px;
            }
            QScrollBar::handle:vertical:hover { background: #3a608a; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QStatusBar { background: #080e16; color: #557; }
        """)

    def _next_style(self) -> str:
        return """
            QPushButton {
                background: #1a3050; color: #a0d0ff; border: 1px solid #2a5070;
                border-radius: 6px; font-size: 13px; padding: 0 16px;
            }
            QPushButton:hover { background: #254570; }
            QPushButton:disabled { background: #111820; color: #445; border-color: #222; }
        """

    def _finish_style(self) -> str:
        return """
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #006622, stop:1 #008833);
                color: #aaffbb; border: 1px solid #00aa44;
                border-radius: 6px; font-size: 13px; padding: 0 16px; font-weight: bold;
            }
            QPushButton:hover { background: #009944; }
        """
