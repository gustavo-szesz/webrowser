from PyQt5.QtGui import QFont, QPainter, QFontMetrics
from PyQt5.QtWidgets import QSizePolicy
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtWidgets import QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout, QApplication, QLineEdit, QTextEdit, QHBoxLayout, QDialog, QTextBrowser, QMessageBox
from engine import URL, load_html, render_text
from ui.utils.word_layout import WordLayoutWidget

try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView
    WEBENGINE_AVAILABLE = True
except Exception:
    QWebEngineView = None
    WEBENGINE_AVAILABLE = False



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

        layout_btn = QPushButton("Layout")
        layout_btn.clicked.connect(self.view_layout)

        render_btn = QPushButton("Render")
        render_btn.clicked.connect(self.view_render)
        # disable the button if QWebEngineView is not available
        render_btn.setEnabled(WEBENGINE_AVAILABLE)
        if not WEBENGINE_AVAILABLE:
            render_btn.setToolTip("Install PyQtWebEngine to enable full HTML/CSS rendering")

        h.addWidget(self.search)
        h.addWidget(go)
        h.addWidget(source_btn)
        h.addWidget(layout_btn)
        h.addWidget(render_btn)

    def navigate(self):
        text = self.search.text().strip()
        if not text:
            return
        if "://" not in text:
            text = "http://" + text
        try:
            u = URL(text)
            raw = load_html(text)
            self.last_raw = raw
            self.output.setHtml(raw)
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

    def view_layout(self):
        # if we don't have raw HTML yet, try to fetch current url
        if not self.last_raw:
            self.navigate()
            if not self.last_raw:
                return

        dlg = QDialog(self)
        dlg.setWindowTitle("Layout Preview")
        dlg.resize(800, 600)
        vbox = QVBoxLayout(dlg)
        widget = WordLayoutWidget(dlg)
        widget.setFont(QFont("Arial", 12))
        # pass raw HTML so lex can see <b>/<i> tags
        widget.setText(self.last_raw)
        vbox.addWidget(widget)
        dlg.exec_()

    def view_render(self):
        # if we don't have raw HTML yet, try to fetch current url
        if not self.last_raw:
            self.navigate()
            if not self.last_raw:
                return

        if not WEBENGINE_AVAILABLE:
            QMessageBox.critical(self, "Error", "PyQtWebEngine is not installed.\nInstall it with: pip install PyQtWebEngine")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Render (HTML+CSS)")
        dlg.resize(1024, 768)
        vbox = QVBoxLayout(dlg)
        web = QWebEngineView(dlg)
        # Provide a base URL so relative links and resources can resolve if present
        web.setHtml(self.last_raw, QUrl("http://localhost/"))
        vbox.addWidget(web)
        dlg.exec_()