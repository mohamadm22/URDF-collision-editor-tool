"""
ShapeListPanel — shows all shapes for the current mesh with add/delete controls.
"""

from __future__ import annotations
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QMenu, QLabel, QFrame,
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont, QColor, QIcon


_SHAPE_ICON = {"CylinderShape": "⬤", "BoxShape": "■", "SphereShape": "●"}
_SHAPE_COLOR = {
    "CylinderShape": "#4a9eff",
    "BoxShape": "#4aff88",
    "SphereShape": "#ff9944",
}


class ShapeListPanel(QWidget):
    shape_selected = pyqtSignal(str)          # shape_id
    shape_delete_requested = pyqtSignal(str)  # shape_id
    add_shape_requested = pyqtSignal(str)     # shape_type e.g. "CylinderShape"

    def __init__(self, parent=None):
        super().__init__(parent)
        self._shape_ids: list = []
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(4)

        # Header
        header = QHBoxLayout()
        lbl = QLabel("Collision Shapes")
        lbl.setStyleSheet("color: #a0c4ff; font-weight: bold; font-size: 12px;")
        header.addWidget(lbl)
        header.addStretch()

        # Add button with dropdown
        self._add_btn = QPushButton("＋ Add Shape")
        self._add_btn.setFixedHeight(28)
        self._add_btn.setStyleSheet("""
            QPushButton {
                background: #1a3a5c; color: #a0d4ff; border: 1px solid #2a5a8c;
                border-radius: 5px; padding: 0 10px; font-size: 12px;
            }
            QPushButton:hover { background: #225588; }
            QPushButton::menu-indicator { image: none; }
        """)
        menu = QMenu(self._add_btn)
        menu.setStyleSheet("""
            QMenu {
                background: #1a2538; color: #ccd;
                border: 1px solid #334; border-radius: 4px;
            }
            QMenu::item:selected { background: #2a4a6c; }
        """)
        menu.addAction("⬤  Cylinder", lambda: self.add_shape_requested.emit("CylinderShape"))
        menu.addAction("■  Box",      lambda: self.add_shape_requested.emit("BoxShape"))
        menu.addAction("●  Sphere",   lambda: self.add_shape_requested.emit("SphereShape"))
        self._add_btn.setMenu(menu)
        header.addWidget(self._add_btn)
        root.addLayout(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: #334;")
        root.addWidget(sep)

        # List
        self._list = QListWidget()
        self._list.setStyleSheet("""
            QListWidget {
                background: #111928; color: #ccd;
                border: 1px solid #2a3a4a; border-radius: 5px;
                outline: none;
            }
            QListWidget::item {
                padding: 6px 8px; border-bottom: 1px solid #1e2a38;
            }
            QListWidget::item:selected {
                background: #1e3d5c; color: white;
                border-left: 3px solid #4a9eff;
            }
            QListWidget::item:hover { background: #192535; }
        """)
        self._list.currentItemChanged.connect(self._on_selection_changed)
        # itemClicked fires even when the item is already selected —
        # this lets the user re-open the property panel by clicking again
        self._list.itemClicked.connect(self._on_item_clicked)
        root.addWidget(self._list, 1)

        # Delete button
        self._del_btn = QPushButton("🗑  Delete Selected")
        self._del_btn.setEnabled(False)
        self._del_btn.setFixedHeight(28)
        self._del_btn.setStyleSheet("""
            QPushButton {
                background: #3a1a1a; color: #ff8888; border: 1px solid #6a2a2a;
                border-radius: 5px; padding: 0 10px; font-size: 12px;
            }
            QPushButton:hover { background: #5a2222; }
            QPushButton:disabled { background: #1e1e1e; color: #555; border-color: #333; }
        """)
        self._del_btn.clicked.connect(self._on_delete)
        root.addWidget(self._del_btn)

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def refresh(self, shapes: list) -> None:
        """Repopulate the list from a list of BaseShape objects."""
        current_id = self._current_id()
        self._list.blockSignals(True)
        self._list.clear()
        self._shape_ids.clear()

        for shape in shapes:
            type_name = type(shape).__name__
            icon = _SHAPE_ICON.get(type_name, "○")
            color = _SHAPE_COLOR.get(type_name, "#ccd")
            item = QListWidgetItem(f"{icon}  {shape.name}")
            item.setForeground(QColor(color))
            item.setData(Qt.ItemDataRole.UserRole, shape.id)
            self._list.addItem(item)
            self._shape_ids.append(shape.id)

        self._list.blockSignals(False)

        # Restore selection
        if current_id in self._shape_ids:
            idx = self._shape_ids.index(current_id)
            self._list.setCurrentRow(idx)
        elif self._list.count() > 0:
            self._list.setCurrentRow(0)

        self._del_btn.setEnabled(self._list.count() > 0)

    def clear(self):
        self._list.clear()
        self._shape_ids.clear()
        self._del_btn.setEnabled(False)

    def select_shape_id(self, shape_id: str):
        for i, sid in enumerate(self._shape_ids):
            if sid == shape_id:
                self._list.setCurrentRow(i)
                return

    # ------------------------------------------------------------------ #
    # Slots                                                                #
    # ------------------------------------------------------------------ #

    def _on_selection_changed(self, current, _previous):
        if current is None:
            self._del_btn.setEnabled(False)
            return
        shape_id = current.data(Qt.ItemDataRole.UserRole)
        self._del_btn.setEnabled(True)
        self.shape_selected.emit(shape_id)

    def _on_item_clicked(self, item):
        """Always emit shape_selected, even when clicking the current row."""
        if item is None:
            return
        shape_id = item.data(Qt.ItemDataRole.UserRole)
        self._del_btn.setEnabled(True)
        self.shape_selected.emit(shape_id)

    def _on_delete(self):
        shape_id = self._current_id()
        if shape_id:
            self.shape_delete_requested.emit(shape_id)

    def _current_id(self) -> str | None:
        item = self._list.currentItem()
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None
