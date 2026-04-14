"""
TLREF Pricer — Local Launcher
Double-click this file or run: python run_pricer.py
Opens the React pricer in your default browser.
"""
import http.server
import os
import re
import threading
import webbrowser

PORT = 8765
ROOT = os.path.dirname(os.path.abspath(__file__))
JSX_PATH = os.path.join(ROOT, "frontend", "tlref-ois-pricer.jsx")

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TLREF OIS Pricer - FETM Research</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #060A14; }
  #root { min-height: 100vh; }
</style>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=DM+Sans:wght@400;500;700&display=swap" rel="stylesheet">
</head>
<body>
<div id="root"><div style="color:#8B949E;padding:40px;text-align:center;font-family:monospace">Loading TLREF Pricer...</div></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/react/18.2.0/umd/react.production.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/react-dom/18.2.0/umd/react-dom.production.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/babel-standalone/7.23.9/babel.min.js"></script>
<script type="text/babel">
{{JSX_PLACEHOLDER}}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(React.createElement(App));
</script>
</body>
</html>"""


def load_jsx():
    with open(JSX_PATH, "r", encoding="utf-8") as f:
        code = f.read()
    # Strip ES module import — use React globals instead
    code = re.sub(
        r'import\s*\{[^}]+\}\s*from\s*["\']react["\'];?',
        'const { useState, useMemo, useCallback } = React;',
        code
    )
    # Strip export default
    code = code.replace("export default function App", "function App")
    return code


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        jsx = load_jsx()
        html = HTML_TEMPLATE.replace("{{JSX_PLACEHOLDER}}", jsx)
        self.wfile.write(html.encode("utf-8"))

    def log_message(self, fmt, *args):
        pass  # silent


def main():
    if not os.path.exists(JSX_PATH):
        print(f"ERROR: {JSX_PATH} not found!")
        print("Run 'git pull' first.")
        input("Press Enter to exit...")
        return

    httpd = http.server.HTTPServer(("127.0.0.1", PORT), Handler)
    print(f"TLREF Pricer at http://localhost:{PORT}")
    print("Press Ctrl+C to stop.\n")
    threading.Timer(1.0, lambda: webbrowser.open(f"http://localhost:{PORT}")).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        httpd.shutdown()


if __name__ == "__main__":
    main()

