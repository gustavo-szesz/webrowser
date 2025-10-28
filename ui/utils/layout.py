from PyQt5.QtGui import QFont, QPainter, QFontMetrics
from PyQt5.QtWidgets import QSizePolicy
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtWidgets import QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout, QApplication, QLineEdit, QTextEdit, QHBoxLayout, QDialog, QTextBrowser, QMessageBox
from ui.main_window import Tag, Text, lex



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

