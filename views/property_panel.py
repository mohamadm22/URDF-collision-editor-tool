"""
PropertyPanel — dynamically renders editable fields for the selected shape.
"""

from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox,
    QLineEdit, QPushButton, QFrame, QScrollArea, QSizePolicy,
    QGroupBox, QFileDialog,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont
from models.shapes.base_shape import BaseShape
from models.shapes.cylinder_shape import CylinderShape
from models.shapes.box_shape import BoxShape
from models.shapes.sphere_shape import SphereShape
from models.shapes.stl_shape import StlShape


class _FieldSpinBox(QDoubleSpinBox):
    def __init__(self, min_v=-999.0, max_v=999.0, decimals=4, step=0.01, parent=None):
        super().__init__(parent)
        self.setRange(min_v, max_v)
        self.setDecimals(decimals)
        self.setSingleStep(step)
        self.setMinimumWidth(80)


class PropertyPanel(QWidget):
    """Right-panel: shows editable parameters for the currently selected shape."""

    # Emitted when user clicks Apply with (shape_id, params_dict)
    shape_updated = pyqtSignal(str, dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_shape: BaseShape | None = None
        self._fields: dict = {}   # param_name -> widget
        self._setup_ui()

    # ------------------------------------------------------------------ #
    # UI construction                                                      #
    # ------------------------------------------------------------------ #

    def _setup_ui(self):
        self.setMinimumWidth(240)
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # Title
        self._title = QLabel("No shape selected")
        self._title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self._title.setFont(font)
        self._title.setStyleSheet("color: #a0c4ff; padding: 4px;")
        root.addWidget(self._title)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #444;")
        root.addWidget(sep)

        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(4)
        self._content_layout.addStretch()
        scroll.setWidget(self._content)
        root.addWidget(scroll, 1)

        # Apply button
        self._apply_btn = QPushButton("✔  Apply Changes")
        self._apply_btn.setEnabled(False)
        self._apply_btn.setMinimumHeight(36)
        self._apply_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0066cc, stop:1 #0044aa);
                color: white; border-radius: 6px; font-weight: bold;
            }
            QPushButton:hover { background: #0077ee; }
            QPushButton:disabled { background: #333; color: #666; }
        """)
        self._apply_btn.clicked.connect(self._on_apply)
        root.addWidget(self._apply_btn)

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def load_shape(self, shape: BaseShape | None) -> None:
        self._current_shape = shape
        self._clear_content()
        self._fields.clear()

        if shape is None:
            self._title.setText("No shape selected")
            self._apply_btn.setEnabled(False)
            return

        self._title.setText(f"✦ {shape.name}")
        self._apply_btn.setEnabled(True)

        # Name field
        self._add_group("Identity", [
            ("Name", self._make_line_edit("name", shape.name)),
        ])

        # Dimension fields
        dim_fields = []
        if isinstance(shape, CylinderShape):
            dim_fields = [
                ("Radius (m)", self._make_spin("radius", shape.radius, 0.0001, 1e6, 0.001)),
                ("Length (m)", self._make_spin("length", shape.length, 0.0001, 1e6, 0.001)),
            ]
        elif isinstance(shape, BoxShape):
            dim_fields = [
                ("Size X (m)", self._make_spin("size_x", shape.size_x, 0.0001, 1e6, 0.001)),
                ("Size Y (m)", self._make_spin("size_y", shape.size_y, 0.0001, 1e6, 0.001)),
                ("Size Z (m)", self._make_spin("size_z", shape.size_z, 0.0001, 1e6, 0.001)),
            ]
        elif isinstance(shape, SphereShape):
            dim_fields = [
                ("Radius (m)", self._make_spin("radius", shape.radius, 0.0001, 1e6, 0.001)),
            ]
        elif isinstance(shape, StlShape):
            # STL Path with browse button
            path_row = self._make_line_edit("stl_path", shape.stl_path)
            browse_btn = QPushButton("...")
            browse_btn.setFixedWidth(30)
            browse_btn.clicked.connect(self._on_browse_stl)
            
            # Pack browse button and path in a layout
            path_host = QWidget()
            path_lay = QHBoxLayout(path_host)
            path_lay.setContentsMargins(0, 0, 0, 0)
            path_lay.setSpacing(2)
            path_lay.addWidget(path_row, 1)
            path_lay.addWidget(browse_btn)
            
            self._add_group("Collision Mesh", [
                ("STL Path", path_host),
            ])
            
            # User scale fields
            sx, sy, sz = shape.scale
            dim_fields = [
                ("Scale X", self._make_spin("scale_x", sx, 0.0001, 1e6, 0.001)),
                ("Scale Y", self._make_spin("scale_y", sy, 0.0001, 1e6, 0.001)),
                ("Scale Z", self._make_spin("scale_z", sz, 0.0001, 1e6, 0.001)),
            ]
        self._add_group("Dimensions", dim_fields)

        # Position
        px, py, pz = shape.position
        self._add_group("Position (world)", [
            ("X (m)", self._make_spin("pos_x", px, -1e6, 1e6, 0.01)),
            ("Y (m)", self._make_spin("pos_y", py, -1e6, 1e6, 0.01)),
            ("Z (m)", self._make_spin("pos_z", pz, -1e6, 1e6, 0.01)),
        ])

        # Orientation in degrees
        roll, pitch, yaw = shape.orientation_deg
        self._add_group("Orientation (degrees)", [
            ("Roll  °", self._make_spin("roll_deg",  roll,  -360, 360, 1.0)),
            ("Pitch °", self._make_spin("pitch_deg", pitch, -360, 360, 1.0)),
            ("Yaw   °", self._make_spin("yaw_deg",   yaw,   -360, 360, 1.0)),
        ])

        # Push remaining space down
        self._content_layout.addStretch()

    def clear(self):
        self.load_shape(None)

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _clear_content(self):
        # Remove all widgets from content layout except the trailing stretch
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _add_group(self, title: str, rows: list):
        if not rows:
            return
        box = QGroupBox(title)
        box.setStyleSheet("""
            QGroupBox {
                color: #88aacc; border: 1px solid #334;
                border-radius: 5px; margin-top: 8px; padding-top: 4px;
                font-size: 10px;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 8px; }
        """)
        lay = QVBoxLayout(box)
        lay.setSpacing(3)
        lay.setContentsMargins(6, 4, 6, 4)
        for label_text, widget in rows:
            row = QHBoxLayout()
            lbl = QLabel(label_text)
            lbl.setStyleSheet("color: #ccc; font-size: 11px;")
            lbl.setMinimumWidth(80)
            row.addWidget(lbl)
            row.addWidget(widget)
            lay.addLayout(row)
        self._content_layout.addWidget(box)

    def _make_spin(self, key: str, value: float,
                   min_v: float, max_v: float, step: float) -> QDoubleSpinBox:
        sb = _FieldSpinBox(min_v, max_v, step=step)
        sb.setValue(value)
        sb.setStyleSheet("""
            QDoubleSpinBox {
                background: #1e2a3a; color: #dde; border: 1px solid #445;
                border-radius: 4px; padding: 2px 4px;
            }
        """)
        self._fields[key] = sb
        return sb

    def _make_line_edit(self, key: str, value: str) -> QLineEdit:
        le = QLineEdit(value)
        le.setStyleSheet("""
            QLineEdit {
                background: #1e2a3a; color: #dde; border: 1px solid #445;
                border-radius: 4px; padding: 2px 6px;
            }
        """)
        self._fields[key] = le
        return le

    # ------------------------------------------------------------------ #
    # Apply                                                                #
    # ------------------------------------------------------------------ #

    def _on_apply(self):
        if self._current_shape is None:
            return

        params = {}

        # Name
        if "name" in self._fields:
            params["name"] = self._fields["name"].text().strip() or self._current_shape.name

        # Position
        for axis, key in enumerate(["pos_x", "pos_y", "pos_z"]):
            if key in self._fields:
                if "position" not in params:
                    params["position"] = list(self._current_shape.position)
                params["position"][axis] = self._fields[key].value()

        # Orientation (degrees)
        deg_keys = ["roll_deg", "pitch_deg", "yaw_deg"]
        if any(k in self._fields for k in deg_keys):
            orient = list(self._current_shape.orientation_deg)
            for i, key in enumerate(deg_keys):
                if key in self._fields:
                    orient[i] = self._fields[key].value()
            params["orientation_deg"] = orient

        # Dimensions
        for key in ["radius", "length", "size_x", "size_y", "size_z"]:
            if key in self._fields:
                params[key] = self._fields[key].value()

        # STL specific
        if "stl_path" in self._fields:
            params["stl_path"] = self._fields["stl_path"].text().strip()
        
        if "scale_x" in self._fields:
            params["scale"] = [
                self._fields["scale_x"].value(),
                self._fields["scale_y"].value(),
                self._fields["scale_z"].value()
            ]

        self.shape_updated.emit(self._current_shape.id, params)

    def _on_browse_stl(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select STL Collision Mesh", "", "STL Files (*.stl);;All Files (*)")
        if path:
            self._fields["stl_path"].setText(path)
