"""
TLREF Pricer — Local Launcher
Double-click this file or run: python run_pricer.py
Opens the React pricer in your default browser.
"""
import http.server
import os
import threading
import webbrowser

PORT = 8765
DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")

os.chdir(DIR)
handler = http.server.SimpleHTTPRequestHandler
httpd = http.server.HTTPServer(("127.0.0.1", PORT), handler)

print(f"TLREF Pricer running at http://localhost:{PORT}")
print("Press Ctrl+C to stop.\n")

threading.Timer(1.0, lambda: webbrowser.open(f"http://localhost:{PORT}")).start()

try:
    httpd.serve_forever()
except KeyboardInterrupt:
    print("\nStopped.")
    httpd.shutdown()
