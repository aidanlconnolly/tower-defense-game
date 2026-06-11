import http.server, socketserver, os

PORT = 5200
DIRECTORY = "/Users/aidanconnolly/Desktop/Projects/Working/Tower defense game"

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)
    def log_message(self, format, *args):
        pass

with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
    httpd.serve_forever()
