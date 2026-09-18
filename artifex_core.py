
from flask import Flask, send_from_directory, render_template_string
import os

app = Flask(__name__, static_folder='static')

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
    return {"status": "ok"}

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
