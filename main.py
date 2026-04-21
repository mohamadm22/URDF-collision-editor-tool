#!/usr/bin/env python3
"""
URDF Collision Editor — entry point.

Usage:
    python main.py
"""

import sys
import os

# Ensure the project root is on the Python path regardless of cwd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from views.main_window import MainWindow
import vtk

# Suppress VTK output window and warnings
vtk_out = vtk.vtkStringOutputWindow()
vtk.vtkOutputWindow.SetInstance(vtk_out)

def main():
    # High-DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("URDF Collision Editor")
    app.setOrganizationName("RoboticsTools")

    # Default application font
    font = QFont("Ubuntu", 11)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
