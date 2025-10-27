from PyQt5.QtGui import QFont, QPainter, QFontMetrics
from PyQt5.QtWidgets import QSizePolicy
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout, QApplication, QLineEdit, QTextEdit, QHBoxLayout, QDialog
from engine import URL, render_text

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

        self.v.addWidget(header)
        self.v.addWidget(searchbar)
        self.v.addWidget(self.output)

        self.setCentralWidget(self.central)


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

        h.addWidget(self.search)
        h.addWidget(go)
        h.addWidget(source_btn)
        h.addWidget(layout_btn)

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
        widget = WordLayoutWidget()
        widget.setFont(QFont("Arial", 12))
        # pass raw HTML so lex can see <b>/<i> tags
        widget.setText(self.last_raw)
        vbox.addWidget(widget)
        dlg.exec_()


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
    # Accept either a raw HTML/text string or a list of tokens
    if isinstance(text, str):
        tokens = None
        # lazy import of lex below
        tokens = lex(text)
    else:
        tokens = text

    base_fm = QFontMetrics(qfont)
    space_w_base = base_fm.horizontalAdvance(' ')
    cursor_x = hstep
    # start y at ascent so text draws inside widget
    line_height = base_fm.height()
    cursor_y = line_height  # first baseline

    display_list = []

    # state for font modifiers
    weight = 'normal'
    style = 'roman'

    for tok in tokens:
        if isinstance(tok, Text):
            # split the text token into words
            for word in tok.text.split():
                # create a font for this run based on modifiers
                f = QFont(qfont)
                f.setBold(weight == 'bold')
                f.setItalic(style == 'italic')
                fm_word = QFontMetrics(f)
                w = fm_word.horizontalAdvance(word)

                # wrap
                if cursor_x + w > max(hstep + 10, width - hstep):
                    cursor_y += int(line_height * 1.25) + vpad
                    cursor_x = hstep

                display_list.append((cursor_x, cursor_y, word, f))
                cursor_x += w + fm_word.horizontalAdvance(' ')

        elif isinstance(tok, Tag):
            t = tok.tag
            # normalize simple tags like 'b', '/b', 'i', '/i'
            if t == 'i':
                style = 'italic'
            elif t == '/i':
                style = 'roman'
            elif t == 'b':
                weight = 'bold'
            elif t == '/b':
                weight = 'normal'
            else:
                # ignore other tags for layout purposes
                pass

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
        # draw each word at computed baseline position using its per-word font
        for item in items:
            # items are (x, y, word, font)
            if len(item) == 4:
                x, y, word, font = item
            else:
                x, y, word = item
                font = self.font()
            painter.setFont(font)
            painter.drawText(x, y, word)

        # optionally draw a guide line at bottom
        painter.setPen(painter.pen())
        painter.end()


