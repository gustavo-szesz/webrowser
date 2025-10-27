import socket
import sys
import ssl
import os
import threading
try:
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import Gtk, Gdk
    import cairo
    GTK_AVAILABLE = True
except Exception:
    GTK_AVAILABLE = False
import tkinter

# Prefer PyQt (works natively on Wayland). Try PyQt6 then PyQt5.
PYQT_AVAILABLE = False
PYQT6 = False
try:
    from PyQt6 import QtWidgets, QtGui, QtCore
    PYQT_AVAILABLE = True
    PYQT6 = True
except Exception:
    try:
        from PyQt5 import QtWidgets, QtGui, QtCore
        PYQT_AVAILABLE = True
    except Exception:
        PYQT_AVAILABLE = False

class URL:
    def __init__(self, url):
        self.scheme, url = url.split("://", 1)
        assert self.scheme in ["http", "https"]

        if self.scheme == "http":
            self.port = 80
        elif self.scheme == "https":
            self.port = 443

        if "/" not in url:
            url = url + "/"
        self.host, url = url.split("/", 1)
        self.path = "/" + url

        # support custom ports like host:8080
        if ":" in self.host:
            host, port = self.host.split(":", 1)
            self.host = host
            self.port = int(port)

    def request(self):
        s = socket.socket(
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP
        )
        s.connect((self.host, self.port))
        if self.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)

        request = "GET {} HTTP/1.0\r\n".format(self.path)
        request += "Host: {}\r\n".format(self.host)
        request += "User-Agent: Webrowser/0.1\r\n"
        request += "\r\n"
        s.send(request.encode("utf8"))
        
        # Debug output
        print("---- REQUEST ----")
        print(request)
        response = s.makefile("r", encoding="utf8", newline="\r\n")

        statusline = response.readline()
        version, status, explanation = statusline.split(" ", 2)

        response_headers = {}
        while True:
            line = response.readline()
            if line == "\r\n": break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()

        assert "transfer-encoding" not in response_headers
        assert "content-encoding" not in response_headers

        content = response.read()
        s.close()
        return content
    
def show(body):
    in_tag = False
    i = 0
    L = len(body)
    while i < L:
        c = body[i]
        if c == '&':
            # try to parse an entity up to the next ';'
            semi = body.find(';', i + 1)
            if semi != -1:
                ent = body[i+1:semi]
                if ent == "lt":
                    if not in_tag:
                        print("<", end="")
                    i = semi + 1
                    continue
                if ent == "gt":
                    if not in_tag:
                        print(">", end="")
                    i = semi + 1
                    continue
            # unknown entity or no semicolon -> emit '&' literally (if not inside a tag)
            if not in_tag:
                print("&", end="")
            i += 1
            continue

        if c == "<":
            in_tag = True
            i += 1
            continue
        if c == ">":
            in_tag = False
            i += 1
            continue
        if not in_tag:
            print(c, end="")
        i += 1

def load(url):
    body = url.request()
    show(body)

WIDTH = 800
HEIGHT = 600

if PYQT_AVAILABLE:
    # PyQt implementation: window with an address bar, a drawing canvas and a text area.
    class QtCanvas(QtWidgets.QWidget):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setMinimumSize(WIDTH, HEIGHT // 2)

        def paintEvent(self, event):
            p = QtGui.QPainter(self)
            p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
            # white background
            p.fillRect(self.rect(), QtGui.QBrush(QtGui.QColor(255, 255, 255)))
            # rectangle
            p.setBrush(QtGui.QBrush(QtGui.QColor(204, 204, 204)))
            p.drawRect(10, 20, 390, 180)
            # circle
            p.setBrush(QtGui.QBrush(QtGui.QColor(51, 153, 230)))
            p.drawEllipse(100, 100, 50, 50)
            # text
            p.setPen(QtGui.QPen(QtGui.QColor(0, 0, 0)))
            font = QtGui.QFont("Sans", 14)
            p.setFont(font)
            p.drawText(200, 300, "Hello, Webrowser!")
            p.end()

    class Browser(QtWidgets.QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Webrowser (PyQt)")
            self.resize(WIDTH, HEIGHT)

            central = QtWidgets.QWidget()
            self.setCentralWidget(central)
            vbox = QtWidgets.QVBoxLayout(central)

            # address bar
            self.addr = QtWidgets.QLineEdit()
            self.addr.setPlaceholderText("Enter URL or domain and press Enter")
            vbox.addWidget(self.addr)

            # canvas
            self.canvas = QtCanvas()
            vbox.addWidget(self.canvas)

            # text area to show fetched page (plain text)
            self.text = QtWidgets.QTextEdit()
            self.text.setReadOnly(True)
            vbox.addWidget(self.text, stretch=1)

            self.addr.returnPressed.connect(self.on_address_entered)

        def on_address_entered(self):
            q = self.addr.text().strip()
            if not q:
                return
            # normalize to URL if needed
            if "://" not in q:
                q = "http://" + q

            # fetch in a background thread
            def worker(url):
                try:
                    body = URL(url).request()
                except Exception as e:
                    body = f"Error fetching {url}: {e}"
                # schedule update in the Qt main thread
                QtCore.QTimer.singleShot(0, lambda b=body: self.on_fetched(b))

            threading.Thread(target=worker, args=(q,), daemon=True).start()

        def on_fetched(self, body):
            # simple render: strip tags and decode entities like existing show()
            out = []
            in_tag = False
            i = 0
            L = len(body)
            while i < L:
                c = body[i]
                if c == "&":
                    semi = body.find(";", i + 1)
                    if semi != -1:
                        ent = body[i + 1:semi]
                        if ent == "lt":
                            if not in_tag:
                                out.append("<")
                            i = semi + 1
                            continue
                        if ent == "gt":
                            if not in_tag:
                                out.append(">")
                            i = semi + 1
                            continue
                    if not in_tag:
                        out.append("&")
                    i += 1
                    continue
                if c == "<":
                    in_tag = True
                    i += 1
                    continue
                if c == ">":
                    in_tag = False
                    i += 1
                    continue
                if not in_tag:
                    out.append(c)
                i += 1
            self.text.setPlainText("".join(out))
            self.canvas.update()
else:
    # keep the GTK / tkinter fallback definitions as before
    if GTK_AVAILABLE:
        class Browser:
            def __init__(self):
                print("Browser(GTK): creating window", flush=True)
                self.window = Gtk.Window(title="Webrowser (GTK)")
                self.window.set_default_size(WIDTH, HEIGHT)
                self.darea = Gtk.DrawingArea()
                self.darea.set_size_request(WIDTH, HEIGHT)
                self.darea.connect("draw", self.on_draw)
                self.window.add(self.darea)
                self.window.connect("destroy", Gtk.main_quit)
                self.window.show_all()

            def on_draw(self, widget, cr: cairo.Context):
                # white background
                cr.set_source_rgb(1, 1, 1)
                cr.paint()

                # rectangle
                cr.set_source_rgb(0.8, 0.8, 0.8)
                cr.rectangle(10, 20, 400 - 10, 200)
                cr.fill()

                # circle
                cr.set_source_rgb(0.2, 0.6, 0.9)
                cr.arc(125, 125, 25, 0, 2 * 3.14159)
                cr.fill()

                # text
                cr.set_source_rgb(0, 0, 0)
                cr.select_font_face("Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
                cr.set_font_size(20)
                cr.move_to(200, 300)
                cr.show_text("Hello, Webrowser!")
                return False

            def load(self, url):
                # placeholder: in GTK we might trigger re-draw or fetch content async
                self.darea.queue_draw()
    else:
        # fallback to the existing tkinter-based Browser
        class Browser:
            def __init__(self):
                print("Browser.__init__: before Tk()", flush=True)
                try:
                    self.window = tkinter.Tk()
                except Exception as e:
                    print("Browser.__init__: Tk() raised:", repr(e), flush=True)
                    raise
                print("Browser.__init__: after Tk()", flush=True)
                
                try:
                    print("Browser.__init__: creating Canvas()", flush=True)
                    self.canvas = tkinter.Canvas(
                        self.window,
                        width=WIDTH,
                        height=HEIGHT
                    )
                    print("Browser.__init__: packing Canvas()", flush=True)
                    self.canvas.pack()
                    print("Browser.__init__: Canvas ready", flush=True)
                except Exception as e:
                    print("Browser.__init__: Canvas setup raised:", repr(e), flush=True)
                    raise

            def load(self, url):
                self.canvas.create_rectangle(10, 20, 400, 200)
                self.canvas.create_oval(100, 100, 150, 150)
                self.canvas.create_text(200, 300, text="Hello, Webrowser!")
                self.canvas.create_line(0, 0, 400, 400)

        
if __name__ == "__main__":
    import traceback
    print("webrowser: start")
    print("env DISPLAY =", os.environ.get("DISPLAY"))
    print("env WAYLAND_DISPLAY =", os.environ.get("WAYLAND_DISPLAY"))

    try:
        print("webrowser: creating Browser()")
        browser = Browser()
        print("webrowser: Browser created")
    except Exception as e:
        print("webrowser: failed to create Browser() — falling back to headless")
        traceback.print_exc()
        # headless fallback: fetch URL if provided, else exit
        if len(sys.argv) > 1:
            try:
                body = URL(sys.argv[1]).request()
                show(body)
            except Exception as e2:
                print("Error (headless):", e2)
        else:
            print("Run with a URL arg to fetch headless: python browser.py http://example.org/")
        sys.exit(0)

    if len(sys.argv) > 1:
        def do_load():
            try:
                browser.load(URL(sys.argv[1]))
            except Exception as e:
                print("Error loading URL:", e)
        browser.window.after(50, lambda: threading.Thread(target=do_load, daemon=True).start())

    print("webrowser: entering mainloop")
    try:
        tkinter.mainloop()
    except Exception:
        print("mainloop raised exception")
        traceback.print_exc()