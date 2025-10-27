from PyQt5.QtGui import QFont, QPainter, QFontMetrics
from PyQt5.QtWidgets import QSizePolicy
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout, QApplication, QLineEdit, QTextEdit, QHBoxLayout, QDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Web Browser (text mode)")
        self.resize(800, 600)
        self.font = QFont("Arial", 10)

        self.setFont(self.font)

        for word in QApplication.instance().font().families():
            print("Available font:", word)
            self.font = QFont(word, 10)
            self.setFont(self.font)
            print("Set font to:", word)

        self.central = QWidget()
        self.v = QVBoxLayout(self.central)

        header = QLabel("Web Browser (text mode)")
        header.setFont(QFont("Sans", 12))

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Courier", 10))

        # add search bar with Go and Source
        searchbar = QtSearchBar(self.output, parent=self)

        v.addWidget(header)
        v.addWidget(searchbar)
        v.addWidget(self.output)

        self.setCentralWidget(central)


class QtSearchBar(QWidget):
    """A small widget with a QLineEdit and Go/Source buttons that talks to an output QTextEdit.

    Usage: place an instance into a layout and pass the QTextEdit that will display results.
    """
    def __init__(self, output_widget, parent=None):
        super().__init__(parent)
        self.output = output_widget
        self.last_raw = None

        h = QHBoxLayout(self)

        self.search = QLineEdit(self)
        self.search.setMaxLength(2048)
        self.search.setAlignment(Qt.AlignLeft)
        self.search.setFont(QFont("Arial", 12))
        self.search.setPlaceholderText("Digite uma URL (ex: example.com ou http://example.com)")

        go = QPushButton("Go")
        go.clicked.connect(self.navigate)
        self.search.returnPressed.connect(self.navigate)

        source_btn = QPushButton("Source")
        source_btn.clicked.connect(self.view_source)

        h.addWidget(self.search)
        h.addWidget(go)
        h.addWidget(source_btn)

    def navigate(self):
        text = self.search.text().strip()
        if not text:
            return
        if "://" not in text:
            text = "http://" + text
        try:
            u = URL(text)
            raw = u.request()
            rendered = render_text(raw)
            self.last_raw = raw
            self.output.setPlainText(rendered)
        except Exception as e:
            self.output.setPlainText("Erro: " + str(e))

    def view_source(self):
        # if we don't have raw HTML yet, try to fetch current url
        if not self.last_raw:
            self.navigate()
            if not self.last_raw:
                return

        dlg = QDialog(self)
        dlg.setWindowTitle("View Source")
        dlg.resize(800, 600)
        vbox = QVBoxLayout(dlg)
        te = QTextEdit(dlg)
        te.setPlainText(self.last_raw)
        te.setReadOnly(True)
        te.setFont(QFont("Courier", 10))
        vbox.addWidget(te)
        dlg.exec_()


def layout_text(text, qfont, width, hstep=10, vpad=8):
    """Layout words from `text` using QFontMetrics.

    Returns a list of tuples: (x, y, word). Arguments:
    - text: the input string
    - qfont: QFont instance used for measurement
    - width: available width in pixels
    - hstep: left/right margin in pixels
    - vpad: extra vertical padding multiplier (in pixels)

    Behavior mirrors the tkinter example: words are placed left-to-right,
    wrapping to the next line when they exceed `width - hstep`.
    """
    fm = QFontMetrics(qfont)
    space_w = fm.horizontalAdvance(' ')
    cursor_x = hstep
    # start y at ascent so text draws inside widget
    line_height = fm.height()
    cursor_y = line_height  # first baseline

    display_list = []

    # simple split on whitespace; keeps identical semantics to the tkinter/old code
    for word in text.split():
        w = fm.horizontalAdvance(word)
        # wrap
        if cursor_x + w > max(hstep + 10, width - hstep):
            cursor_y += int(line_height * 1.25) + vpad
            cursor_x = hstep

        display_list.append((cursor_x, cursor_y, word))
        cursor_x += w + space_w

    return display_list


class WordLayoutWidget(QWidget):
    """Widget that visualizes word layout calculated with `layout_text`.

    Usage: create, call `setText(text)` and show. It uses the widget's font by default.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._text = ''
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def setText(self, text: str):
        self._text = text
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setFont(self.font())
        width = max(100, self.width())
        items = layout_text(self._text, self.font(), width)
        fm = QFontMetrics(self.font())
        # draw each word at computed baseline position
        for x, y, word in items:
            painter.drawText(x, y, word)

        # optionally draw a guide line at bottom
        painter.setPen(painter.pen())
        painter.end()


