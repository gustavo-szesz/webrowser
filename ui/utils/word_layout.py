from PyQt5.QtGui import QFont, QPainter, QFontMetrics
from PyQt5.QtWidgets import QSizePolicy
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtWidgets import QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout, QApplication, QLineEdit, QTextEdit, QHBoxLayout, QDialog, QTextBrowser, QMessageBox
from engine import URL, load_html, render_text

# Try to import QWebEngineView for full HTML+CSS rendering. If absent, keep a flag
# so we can gracefully disable the feature and show an informative message.
try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView
    WEBENGINE_AVAILABLE = True
except Exception:
    QWebEngineView = None
    WEBENGINE_AVAILABLE = False

class WordLayoutWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._text = ''
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def setText(self, text: str):
        self._text = text
        self.update()

    def paintEvent(self, event):
        # lazy import to avoid circular import at module import time
        from ui.utils.layout import layout_text

        painter = QPainter(self)
        painter.setFont(self.font())
        width = max(100, self.width())
        items = layout_text(self._text, self.font(), width)

        for item in items:
            if len(item) == 4:
                x, y, word, font = item
            else:
                x, y, word = item
                font = self.font()
            painter.setFont(font)
            painter.drawText(x, y, word)

        painter.setPen(painter.pen())
        painter.end()