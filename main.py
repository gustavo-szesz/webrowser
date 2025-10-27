import sys

from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow

# import engine functions/classes from engine.py
from engine import URL, render_text, load


if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())