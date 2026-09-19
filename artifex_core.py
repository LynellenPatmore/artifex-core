from functools import wraps
import os
from flask import Flask, jsonify, request, render_template_string
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.url_map.strict_slashes = False
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///artifex.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

API_KEY = os.environ.get("API_KEY", "artifex-secret-key-123")

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_key = request.headers.get('X-API-Key')
        if user_key and user_key == API_KEY:
            return f(*args, **kwargs)
        return jsonify({"error": "Unauthorized: Missing or invalid API key"}), 401
    return decorated_function

class Record(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    def to_dict(self):
        return {"id": self.id, "name": self.name}

with app.app_context():
    db.create_all()

@app.route('/', methods=['GET'])
def home():
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Artifex Dashboard</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .card { background: #1e293b; padding: 2rem 3rem; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); text-align: center; max-width: 500px; width: 100%; }
            h1 { color: #38bdf8; margin-bottom: 0.5rem; }
            p { color: #94a3b8; margin-bottom: 1.5rem; }
            .btn { display: inline-block; background: #0284c7; color: white; padding: 0.75rem 1.5rem; border-radius: 6px; text-decoration: none; font-weight: 600; transition: background 0.2s; }
            .btn:hover { background: #0369a1; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>Artifex Dashboard</h1>
            <p>Welcome to the Artifex Core API. Your backend and database are live and operational.</p>
            <a href="/apidocs" class="btn">Open API Docs (Swagger)</a>
        </div>
    </body>
    </html>
    """
    return render_template_string(html_template), 200

@app.route('/health', methods=['GET'])
@app.route('/health/external', methods=['GET'])
def health_external():
    return jsonify({"status": "ok"}), 200

@app.route('/apispec_1.json', methods=['GET'])
def apispec():
    return jsonify({
        "swagger": "2.0",
        "info": {"title": "Artifex Core API", "version": "1.0.0"},
        "paths": {
            "/health": {
                "get": {"summary": "Health Check", "responses": {"200": {"description": "ok"}}}
            },
            "/records": {
                "get": {"summary": "Get all records", "responses": {"200": {"description": "Success"}}},
                "post": {"summary": "Create record", "responses": {"201": {"description": "Created"}}}
            }
        }
    })

@app.route('/apidocs', methods=['GET'])
@app.route('/apidocs/', methods=['GET'])
def custom_apidocs():
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Artifex Core - API Documentation</title>
        <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui.css" />
        <style>
            body { margin: 0; background: #0f172a; }
            .swagger-ui .topbar { background-color: #1e293b; }
        </style>
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script src="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-bundle.js"></script>
        <script>
            window.onload = function() {
                SwaggerUIBundle({
                    url: "/apispec_1.json",
                    dom_id: '#swagger-ui',
                    presets: [
                        SwaggerUIBundle.presets.apis,
                        SwaggerUIBundle.StandaloneLayout
                    ],
                });
            };
        </script>
    </body>
    </html>
    """)

@app.route('/records', methods=['GET'])
def get_records():
    records = Record.query.all()
    return jsonify([r.to_dict() for r in records]), 200

@app.route('/records', methods=['POST'])
@require_api_key
def add_record():
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({"error": "Invalid request, 'name' is required"}), 400
    new_record = Record(name=data['name'])
    db.session.add(new_record)
    db.session.commit()
    return jsonify(new_record.to_dict()), 201

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)