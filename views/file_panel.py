"""
FilePanel — left sidebar listing all loaded STL files.
"""

from __future__ import annotations
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QLabel, QFrame,
    QLineEdit, QPushButton,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor, QFont


class FilePanel(QWidget):
    file_selected = pyqtSignal(int)   # index into state.meshes
    urdf_selected = pyqtSignal(str)   # path to selected .urdf

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaximumWidth(220)
        self.setMinimumWidth(160)
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(4)

        lbl = QLabel("📁  Loaded Files")
        lbl.setStyleSheet("color: #a0c4ff; font-weight: bold; font-size: 12px; padding: 2px;")
        root.addWidget(lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #334;")
        root.addWidget(sep)

        self._list = QListWidget()
        self._list.setStyleSheet("""
            QListWidget {
                background: #0f1620; color: #bbc;
                border: none; outline: none; font-size: 11px;
            }
            QListWidget::item {
                padding: 6px 8px; border-bottom: 1px solid #1e2a38;
            }
            QListWidget::item:selected {
                background: #1e3d5c; color: white;
                border-left: 3px solid #4a9eff;
            }
            QListWidget::item:hover { background: #141e2e; }
        """)
        self._list.currentRowChanged.connect(self.file_selected.emit)
        root.addWidget(self._list, 1)

        # ── URDF Import Panel ──────────────────────────────────────────
        root.addSpacing(10)
        u_lbl = QLabel("🤖  Link to URDF")
        u_lbl.setStyleSheet("color: #a0c4ff; font-weight: bold; font-size: 11px;")
        root.addWidget(u_lbl)

        u_panel = QWidget()
        u_panel.setStyleSheet("background: #141e2e; border: 1px solid #1e2a38; border-radius: 4px;")
        u_lay = QVBoxLayout(u_panel)
        u_lay.setContentsMargins(6, 6, 6, 6)
        u_lay.setSpacing(6)

        self._urdf_edit = QLineEdit()
        self._urdf_edit.setReadOnly(True)
        self._urdf_edit.setPlaceholderText("No URDF selected...")
        self._urdf_edit.setStyleSheet("""
            QLineEdit {
                background: #080e16; color: #889; border: 1px solid #1a2538;
                padding: 4px; font-size: 10px;
            }
        """)
        u_lay.addWidget(self._urdf_edit)

        self._btn_browse = QPushButton("Browse URDF...")
        self._btn_browse.setStyleSheet("""
            QPushButton {
                background: #1a3050; color: #a0d0ff; border: 1px solid #2a5070;
                border-radius: 4px; padding: 4px; font-size: 11px;
            }
            QPushButton:hover { background: #254570; }
        """)
        self._btn_browse.clicked.connect(self._on_browse_urdf)
        u_lay.addWidget(self._btn_browse)

        root.addWidget(u_panel)

    def _on_browse_urdf(self):
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "Select URDF File", "", "URDF Files (*.urdf);;All Files (*)"
        )
        if path:
            self.set_urdf_path(path)
            self.urdf_selected.emit(path)

    def set_urdf_path(self, path: str | None):
        if path:
            self._urdf_edit.setText(os.path.basename(path))
            self._urdf_edit.setToolTip(path)
        else:
            self._urdf_edit.setText("")
            self._urdf_edit.setToolTip("")

    # ------------------------------------------------------------------ #

    def refresh(self, meshes: list, active_index: int) -> None:
        self._list.blockSignals(True)
        self._list.clear()
        for i, mesh in enumerate(meshes):
            icon = "▶ " if i == active_index else "   "
            item = QListWidgetItem(f"{icon}{mesh.name}")
            shape_count = len(mesh.shapes)
            if shape_count:
                item.setToolTip(f"{shape_count} shape(s) defined")
                item.setForeground(QColor("#6be86b"))
            else:
                item.setForeground(QColor("#99aabb"))
            self._list.addItem(item)
        self._list.setCurrentRow(active_index)
        self._list.blockSignals(False)

    def clear(self):
        self._list.clear()
