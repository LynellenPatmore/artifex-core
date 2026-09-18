cat << 'EOF' > artifex_core.py
import os
import httpx
from flask import Flask, render_template_string, jsonify

app = Flask(__name__, static_folder='static')

EXTERNAL_SITE_URL = "https://api.github.com"

@app.route('/')
def home():
    html_content = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Artifex Dashboard</title>
    </head>
    <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
        <img src="/static/Aritfex.png" alt="Artifex Logo" style="max-width: 300px;">
        <h1>Artifex Dashboard</h1>
        <p>System operational.</p>
    </body>
    </html>
    '''
    return render_template_string(html_content)

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

@app.route('/health/external')
def external_health():
    try:
        response = httpx.get(EXTERNAL_SITE_URL, timeout=5.0)
        is_reachable = response.status_code == 200
        return jsonify({
            "target_url": EXTERNAL_SITE_URL,
            "status_code": response.status_code,
            "reachable": is_reachable
        }), 200 if is_reachable else 502
    except Exception as e:
        return jsonify({
            "target_url": EXTERNAL_SITE_URL,
            "reachable": False,
            "error": str(e)
        }), 502

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
EOF
