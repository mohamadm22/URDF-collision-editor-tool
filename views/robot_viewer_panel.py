"""
RobotViewerPanel — a dockable panel for displaying the robot visual model.
"""

from __future__ import annotations
from PyQt6.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QLabel, QComboBox, QHBoxLayout, QCheckBox
from PyQt6.QtCore import Qt, pyqtSignal
from models.robot_model import RobotModel

class RobotViewerPanel(QDockWidget):
    """Dockable panel with its own 3D viewport for robot visualization."""
    frame_changed = pyqtSignal(str)
    visual_toggled = pyqtSignal(bool)
    collision_toggled = pyqtSignal(bool)

    def __init__(self, plotter_widget, parent=None):
        super().__init__("🤖 Robot Visual Viewer", parent)
        self.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea | Qt.DockWidgetArea.LeftDockWidgetArea)
        
        # Content widget
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)
        
        # Frame selection row
        frame_row = QHBoxLayout()
        frame_row.addWidget(QLabel("Base Frame:"))
        self._frame_combo = QComboBox()
        self._frame_combo.setStyleSheet("""
            QComboBox { 
                background: #1a2538; color: #ccd; border: 1px solid #2a3a4a; 
                padding: 2px 4px; border-radius: 3px; min-width: 100px;
            }
        """)
        self._frame_combo.currentTextChanged.connect(self.frame_changed.emit)
        frame_row.addWidget(self._frame_combo, 1)
        layout.addLayout(frame_row)
        
        # Layer Visibility Toggles
        toggle_row = QHBoxLayout()
        self._visual_cb = QCheckBox("Visual Meshes")
        self._visual_cb.setChecked(True)
        self._visual_cb.toggled.connect(self.visual_toggled.emit)
        
        self._collision_cb = QCheckBox("Collision Shapes")
        self._collision_cb.setChecked(True)
        self._collision_cb.toggled.connect(self.collision_toggled.emit)
        
        toggle_row.addWidget(self._visual_cb)
        toggle_row.addWidget(self._collision_cb)
        layout.addLayout(toggle_row)
        
        # 3D Viewport
        self._plotter_widget = plotter_widget
        layout.addWidget(self._plotter_widget, 1)
        
        # Status Label
        self._status_label = QLabel("No robot loaded.")
        self._status_label.setStyleSheet("color: #88aacc; font-size: 11px; padding: 4px; background: #080e16;")
        layout.addWidget(self._status_label)
        
        self.setWidget(content)
        self._apply_style()

    def update_model(self, model: RobotModel):
        """Updates the frame selector and status info."""
        self._frame_combo.blockSignals(True)
        current = self._frame_combo.currentText()
        self._frame_combo.clear()
        self._frame_combo.addItems(model.frame_names)
        
        # Restore selection or default to map
        if current in model.frame_names:
            self._frame_combo.setCurrentText(current)
        elif "map" in model.frame_names:
            self._frame_combo.setCurrentText("map")
        elif model.frame_names:
            self._frame_combo.setCurrentIndex(0)
            
        self._frame_combo.blockSignals(False)
        
        self.update_status(model)

    def update_status(self, model: RobotModel):
        """Updates the status label with info from the robot model."""
        link_count = len(model.links)
        visual_count = sum(len(link.visuals) for link in model.links.values())
        warning_count = len(model.load_warnings)
        
        msg = f"Links: {link_count} | Visuals: {visual_count}"
        if warning_count > 0:
            msg += f" | ⚠️ Warnings: {warning_count}"
            
        self._status_label.setText(msg)

    def _apply_style(self):
        """Matches the application dark theme."""
        self.setStyleSheet("""
            QDockWidget {
                color: #a0c4ff;
                font-weight: bold;
                titlebar-close-icon: url(none);
                titlebar-normal-icon: url(none);
            }
            QDockWidget::title {
                background: #080e16;
                padding-left: 10px;
                padding-top: 4px;
            }
        """)
