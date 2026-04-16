"""
FilePanel — left sidebar listing all loaded STL files.
"""

from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QLabel, QFrame,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor, QFont


class FilePanel(QWidget):
    file_selected = pyqtSignal(int)   # index into state.meshes

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
        self._list.blockSignals(False)
        self._list.setCurrentRow(active_index)

    def clear(self):
        self._list.clear()
