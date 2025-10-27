import socket
import sys
import ssl
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout, QApplication, QLineEdit, QTextEdit, QHBoxLayout


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
        request += "\r\n"
        s.send(request.encode("utf8"))
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
    
def render_text(body):
    # remove tags, return plain text
    out = []
    in_tag = False
    for c in body:
        if c == "<":
            in_tag = True
        elif c == ">":
            in_tag = False
        elif not in_tag:
            out.append(c)
    return "".join(out)

def load(url):
    # expects a URL instance; returns rendered text
    body = url.request()
    return render_text(body)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple Qt App")
        self.resize(800, 600)

        central = QWidget()
        layout = QVBoxLayout(central)

        label = QLabel("Simple Web Browser (text mode)")
        button = QPushButton("Quit")
        button.clicked.connect(lambda: QApplication.instance().quit())

        # output area for page text
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont("Courier", 10))

        # search bar widget (recebe referência ao output)
        layout.addWidget(label)
        layout.addWidget(QtSearchBar(self.output))
        layout.addWidget(self.output)
        layout.addWidget(button)

        self.setCentralWidget(central)

class QtSearchBar(QWidget):
    def __init__(self, output_widget):
        super().__init__()
        self.output = output_widget

        h = QHBoxLayout(self)

        self.search = QLineEdit(self)
        self.search.setMaxLength(2048)
        self.search.setAlignment(Qt.AlignLeft)
        self.search.setFont(QFont("Arial", 12))
        self.search.setPlaceholderText("Digite uma URL (ex: example.com ou http://example.com)")

        go = QPushButton("Go")
        go.clicked.connect(self.navigate)
        self.search.returnPressed.connect(self.navigate)

        h.addWidget(self.search)
        h.addWidget(go)

    def navigate(self):
        text = self.search.text().strip()
        if not text:
            return
        if "://" not in text:
            text = "http://" + text
        try:
            u = URL(text)
            content = load(u)
            self.output.setPlainText(content)
        except Exception as e:
            self.output.setPlainText("Erro: " + str(e))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())