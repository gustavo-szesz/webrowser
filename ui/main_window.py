from PyQt5.QtGui import QFont, QPainter, QFontMetrics
from PyQt5.QtWidgets import QSizePolicy
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtWidgets import QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout, QApplication, QLineEdit, QTextEdit, QHBoxLayout, QDialog, QTextBrowser, QMessageBox
from engine import URL, load_html, render_text
from ui.utils.word_layout import WordLayoutWidget
from ui.search.searchbar import QtSearchBar

# Try to import QWebEngineView for full HTML+CSS rendering. If absent, keep a flag
# so we can gracefully disable the feature and show an informative message.
try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView
    WEBENGINE_AVAILABLE = True
except Exception:
    QWebEngineView = None
    WEBENGINE_AVAILABLE = False

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

        self.output = QTextBrowser()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Courier", 10))

        # add search bar with Go and Source
        searchbar = QtSearchBar(self.output, parent=self)

        self.v.addWidget(header)
        self.v.addWidget(searchbar)
        self.v.addWidget(self.output)

        self.setCentralWidget(self.central)

class Text:
    def __init__(self, text):
        self.text = text


class Tag:
    def __init__(self, tag):
        # store normalized tag contents (lowercase, stripped)
        self.tag = tag.strip().lower()


def lex(body):
    """Return list of Text and Tag tokens from raw HTML body.

    Text tokens contain runs outside angle brackets. Tag tokens contain
    the raw contents between '<' and '>' (normalized to lower-case and stripped).
    Unfinished tags are discarded.
    """
    out = []
    i = 0
    L = len(body)
    buffer = ""

    ignorable = {'script', 'style'}

    while i < L:
        c = body[i]
        if c == '<':
            # flush any buffered text
            if buffer:
                out.append(Text(buffer))
                buffer = ""

            # find end of tag
            j = body.find('>', i + 1)
            if j == -1:
                # malformed tag; stop parsing
                break
            tag_content = body[i+1:j].strip()
            tag_name = tag_content.split()[0].lower() if tag_content else ''
            out.append(Tag(tag_content))

            # if this is an ignorable tag like <style> or <script>, skip until its close
            if tag_name in ignorable:
                end_tag = f'</{tag_name}>'
                k = body.find(end_tag, j+1)
                if k == -1:
                    # no closing tag; stop parsing after the '>'
                    i = j + 1
                    continue
                else:
                    i = k + len(end_tag)
                    continue
            i = j + 1
        else:
            buffer += c
            i += 1

    if buffer:
        out.append(Text(buffer))
    return out