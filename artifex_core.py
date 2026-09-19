from functools import wraps
import os
from flask import Flask, jsonify, request, render_template_string
from flask_sqlalchemy import SQLAlchemy
from flasgger import Swagger
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///artifex.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
swagger = Swagger(app)

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
    """Artifex Dashboard Home
    ---
    responses:
      200:
        description: Renders the professional SaaS landing page
    """
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Artifex Core | Professional CRUD API & Dashboard</title>
        <!-- Tailwind CSS CDN for modern styling -->
        <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
    </head>
    <body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col justify-between selection:bg-cyan-500 selection:text-white">
        
        <!-- Navbar -->
        <header class="border-b border-slate-800 bg-slate-900/50 backdrop-blur sticky top-0 z-50">
            <div class="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
                <div class="flex items-center space-x-3">
                    <div class="h-3 w-3 rounded-full bg-emerald-500 animate-pulse"></div>
                    <span class="font-bold text-lg tracking-tight text-white">Artifex Core</span>
                </div>
                <nav class="flex items-center space-x-4">
                    <a href="/apidocs" class="text-sm font-medium text-slate-300 hover:text-white transition">API Docs</a>
                    <a href="/records" class="text-sm font-medium text-slate-300 hover:text-white transition">Records Endpoint</a>
                    <a href="https://github.com" target="_blank" class="bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-semibold px-4 py-2 rounded-lg transition border border-slate-700">GitHub</a>
                </nav>
            </div>
        </header>

        <!-- Hero Section -->
        <main class="max-w-6xl mx-auto px-6 py-16 grid grid-cols-1 md:grid-cols-2 gap-12 items-center my-auto">
            <div class="space-y-6">
                <div class="inline-flex items-center space-x-2 bg-cyan-500/10 border border-cyan-500/20 px-3 py-1 rounded-full text-cyan-400 text-xs font-semibold uppercase tracking-wider">
                    <span>Production Ready</span>
                </div>
                <h1 class="text-4xl md:text-5xl font-extrabold tracking-tight text-white leading-tight">
                    Secure, Scalable <span class="text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 to-blue-500">CRUD API Backend</span>
                </h1>
                <p class="text-slate-400 text-lg leading-relaxed">
                    Welcome to Artifex Core. Powered by Flask, SQLAlchemy, and SQLite, featuring robust API key security and interactive OpenAPI documentation.
                </p>
                <div class="flex flex-wrap gap-4 pt-2">
                    <a href="/apidocs" class="bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold px-6 py-3 rounded-xl shadow-lg shadow-cyan-500/20 transition flex items-center space-x-2">
                        <span>Explore Swagger Docs</span>
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3"></path></svg>
                    </a>
                    <a href="/health" class="bg-slate-900 hover:bg-slate-800 text-slate-200 font-semibold px-6 py-3 rounded-xl border border-slate-800 transition">
                        System Health
                    </a>
                </div>
            </div>

            <!-- Publishing Image / Hero Card -->
            <div class="bg-gradient-to-br from-slate-900 to-slate-900/80 p-4 rounded-2xl border border-slate-800 shadow-2xl relative group">
                <div class="absolute inset-0 bg-gradient-to-r from-cyan-500/10 to-blue-500/10 rounded-2xl blur-xl opacity-50 group-hover:opacity-100 transition"></div>
                <!-- Replace the src below with your actual publishing image URL or asset -->
                <div class="relative rounded-xl overflow-hidden bg-slate-950 border border-slate-800 flex items-center justify-center min-h-[300px]">
                    <img src="https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=1000&auto=format&fit=crop" alt="Artifex Publishing Image" class="w-full h-full object-cover rounded-lg opacity-90 hover:scale-105 transition duration-500">
                </div>
                <div class="mt-4 px-2 flex justify-between items-center text-xs text-slate-400 font-mono">
                    <span>STATUS: ONLINE</span>
                    <span>DATABASE: ACTIVE</span>
                </div>
            </div>
        </main>

        <!-- Footer -->
        <footer class="border-t border-slate-800/80 bg-slate-900/30 py-6 text-center text-xs text-slate-500">
            <p>&copy; 2026 Artifex Core. Built with Flask & Render.</p>
        </footer>

    </body>
    </html>
    """
    return render_template_string(html_template), 200

@app.route('/health', methods=['GET'])
@app.route('/health/external', methods=['GET'])
def health_external():
    """Health Check Endpoint
    ---
    responses:
      200:
        description: Returns health status ok
    """
    return jsonify({"status": "ok"}), 200

@app.route('/records', methods=['GET'])
def get_records():
    """Retrieve all records
    ---
    responses:
      200:
        description: A list of all stored records
    """
    records = Record.query.all()
    return jsonify([r.to_dict() for r in records]), 200

@app.route('/records', methods=['POST'])
@require_api_key
def add_record():
    """Create a new record (Protected)
    ---
    parameters:
      - name: X-API-Key
        in: header
        type: string
        required: true
        description: Secret API Key
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
              example: "Sample Artifact"
    responses:
      201:
        description: Record created successfully
      401:
        description: Unauthorized
    """
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({"error": "Invalid request, 'name' is required"}), 400
    
    new_record = Record(name=data['name'])
    db.session.add(new_record)
    db.session.commit()
    return jsonify(new_record.to_dict()), 201

@app.route('/records/<int:record_id>', methods=['PUT'])
@require_api_key
def update_record(record_id):
    """Update an existing record (Protected)
    ---
    parameters:
      - name: X-API-Key
        in: header
        type: string
        required: true
      - name: record_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
              example: "Updated Artifact"
    responses:
      200:
        description: Record updated successfully
      401:
        description: Unauthorized
    """
    record = db.get_or_404(Record, record_id)
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({"error": "Invalid request, 'name' is required"}), 400
    
    record.name = data['name']
    db.session.commit()
    return jsonify(record.to_dict()), 200

@app.route('/records/<int:record_id>', methods=['DELETE'])
@require_api_key
def delete_record(record_id):
    """Delete a record (Protected)
    ---
    parameters:
      - name: X-API-Key
        in: header
        type: string
        required: true
      - name: record_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Record deleted successfully
      401:
        description: Unauthorized
    """
    record = db.get_or_404(Record, record_id)
    db.session.delete(record)
    db.session.commit()
    return jsonify({"message": f"Record {record_id} deleted successfully"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
