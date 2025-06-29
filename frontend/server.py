from http.server import HTTPServer, SimpleHTTPRequestHandler
import os

class FrontendHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.dirname(os.path.abspath(__file__)), **kwargs)

def run_server():
    port = 8080
    server_address = ('', port)
    httpd = HTTPServer(server_address, FrontendHandler)
    print(f"Сервер запущен на порту {port}")
    print(f"Откройте браузер и перейдите по адресу: http://localhost:{port}")
    httpd.serve_forever()

if __name__ == '__main__':
    run_server()
