import socket
import ssl
from urllib.parse import urljoin

# debug flag
DEBUG = False


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

        # compute a usable full URL for this instance (including non-default port)
        if (self.scheme == 'http' and self.port != 80) or (self.scheme == 'https' and self.port != 443):
            hostpart = f"{self.host}:{self.port}"
        else:
            hostpart = self.host
        self.full_url = f"{self.scheme}://{hostpart}{self.path}"

    def request(self, max_redirects=10):
        """Perform a GET request and follow redirects up to max_redirects.

        Returns the response body as a string. Raises on redirect loops or too many
        redirects.
        """
        current_url = self.full_url
        redirects = 0

        while True:
            # build a URL object for this hop so we have host/port/path
            hop = URL(current_url) if not isinstance(current_url, URL) else current_url

            s = socket.socket(
                family=socket.AF_INET,
                type=socket.SOCK_STREAM,
                proto=socket.IPPROTO_TCP
            )
            # avoid hanging forever on connect/read
            s.settimeout(10)
            s.connect((hop.host, hop.port))
            if hop.scheme == "https":
                ctx = ssl.create_default_context()
                s = ctx.wrap_socket(s, server_hostname=hop.host)

            request = "GET {} HTTP/1.0\r\n".format(hop.path)
            request += "Host: {}\r\n".format(hop.host)
            request += "User-Agent: Webrowser/0.1\r\n"
            request += "Connection: close\r\n"
            request += "\r\n"

            #if request == "POST":

            s.send(request.encode("utf8"))
            try:
                # read raw bytes and decode headers
                response = s.makefile("rb") #read as binary
                statusline_b = response.readline()
                
                if not statusline_b:
                    s.close()
                    raise Exception("No response from server")
                statusline = statusline_b.decode('iso-8859-1')
                try:
                    version, status, explanation = statusline.split(" ", 2)
                except ValueError:
                    s.close()
                    raise Exception(f"Malformed status line: {statusline!r}")

                status_code = int(status)

                response_headers = {}
                while True:
                    line_b = response.readline()
                    if line_b == b"\r\n" or line_b == b"":
                        break
                    line = line_b.decode('iso-8859-1')
                    header, value = line.split(":", 1)
                    response_headers[header.casefold()] = value.strip()

                # handle redirects (3xx)
                if 300 <= status_code < 400:
                    location = response_headers.get('location')
                    s.close()
                    if not location:
                        raise Exception(f"Redirect ({status_code}) without Location header")

                    # resolve relative redirects against current URL
                    current_url = urljoin(hop.full_url, location)
                    if DEBUG:
                        print(f"Redirect {status_code}: -> {current_url}")
                    redirects += 1
                    if redirects > max_redirects:
                        raise Exception("Too many redirects")
                    # loop to follow the redirect
                    continue

                # otherwise we expect a real response body
                assert "transfer-encoding" not in response_headers
                assert "content-encoding" not in response_headers

                body_b = response.read()
                s.close()
                # try to decode as utf-8, fall back to latin1 with replacement
                try:
                    return body_b.decode('utf-8')
                except UnicodeDecodeError:
                    return body_b.decode('iso-8859-1', errors='replace')
            except Exception:
                try:
                    s.close()
                except Exception:
                    pass
                raise


def render_text(body):
    # remove tags and ignore contents of <style> and <script>, return plain text
    out = []
    i = 0
    L = len(body)
    ignorable = {'script', 'style'}

    while i < L:
        c = body[i]
        if c == '<':
            # find end of tag
            j = body.find('>', i + 1)
            if j == -1:
                break
            tag_content = body[i+1:j].strip()
            tag_name = tag_content.split()[0].lower() if tag_content else ''

            # if ignorable tag, skip until its close
            if tag_name in ignorable:
                end_tag = f'</{tag_name}>'
                k = body.find(end_tag, j+1)
                if k == -1:
                    i = j + 1
                    continue
                else:
                    i = k + len(end_tag)
                    continue

            # otherwise just skip the tag itself
            i = j + 1
        else:
            out.append(c)
            i += 1

    return ''.join(out)


def load(url):
    # expects a URL instance; returns rendered text
    body = url.request()
    return render_text(body)


def load_html(url):
    "Recebe instância URL ou string 'http://...' -> retorna HTML bruto (str)"
    if isinstance(url, URL):
        return url.request()
    else:
        u = URL(url) if "://" in url else URL("http://" + url)
        return u.request()
