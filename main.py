# -*- coding: utf-8 -*-

from PySide2.QtWidgets import QApplication
import sys
from gui import MainWindow

if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

