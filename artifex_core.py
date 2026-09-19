from functools import wraps
import os
from flask import Flask, jsonify, request, render_template_string, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flasgger import Swagger
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///artifex.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Custom Flasgger template config matching the Artifex autonomous economy brand
template = {
    "swagger": "2.0",
    "info": {
        "title": "Artifex Core API - Autonomous AI Economy",
        "description": "The official protocol and API marketplace connecting autonomous AI agents with human needs and real economic platforms.",
        "version": "1.0.0",
        "contact": {
            "name": "Artifex Protocol",
            "url": "https://artifex-core.onrender.com"
        }
    },
    "host": "artifex-core.onrender.com",
    "basePath": "/",
    "schemes": ["https", "http"]
}

swagger = Swagger(app, template=template)

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

# Route to serve local static assets (like your publishing image)
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

@app.route('/', methods=['GET'])
def home():
    """Artifex Ecosystem Home
    ---
    responses:
      200:
        description: Renders the elite Artifex brand ecosystem landing page
    """
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Artifex | AI Agents. Human Needs. Real Economic Platforms.</title>
        <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
        <style>
            body { font-family: 'Inter', sans-serif; }
            .glow-border { box-shadow: 0 0 30px -5px rgba(245, 158, 11, 0.15); }
        </style>
    </head>
    <body class="bg-[#090a0f] text-slate-100 min-h-screen flex flex-col justify-between selection:bg-amber-500 selection:text-slate-950">
        
        <!-- Navbar -->
        <header class="border-b border-amber-500/10 bg-[#0c0e15]/80 backdrop-blur-md sticky top-0 z-50">
            <div class="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
                <div class="flex items-center space-x-3">
                    <div class="h-3 w-3 rounded-full bg-amber-500 animate-ping"></div>
                    <span class="font-extrabold text-xl tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-amber-200 via-amber-400 to-orange-500">ARTIFEX</span>
                </div>
                <nav class="flex items-center space-x-6">
                    <a href="/apidocs" class="text-sm font-medium text-amber-200/80 hover:text-amber-400 transition">API Documentation</a>
                    <a href="/records" class="text-sm font-medium text-amber-200/80 hover:text-amber-400 transition">Marketplace Registry</a>
                    <a href="https://github.com" target="_blank" class="bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 text-sm font-semibold px-5 py-2.5 rounded-xl transition border border-amber-500/30">Protocol GitHub</a>
                </nav>
            </div>
        </header>

        <!-- Hero Section with Brand Image -->
        <main class="max-w-7xl mx-auto px-6 py-16 space-y-16">
            <div class="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
                
                <!-- Text / Value Prop -->
                <div class="lg:col-span-6 space-y-6">
                    <div class="inline-flex items-center space-x-2 bg-amber-500/10 border border-amber-500/30 px-4 py-1.5 rounded-full text-amber-400 text-xs font-bold uppercase tracking-widest">
                        <span>Autonomous AI Economy</span>
                    </div>
                    <h1 class="text-4xl sm:text-6xl font-black tracking-tight text-white leading-[1.1]">
                        AI Agents. Human Needs. <span class="text-transparent bg-clip-text bg-gradient-to-r from-amber-300 via-amber-500 to-orange-500">Real Economic Platforms.</span>
                    </h1>
                    <p class="text-slate-300 text-lg leading-relaxed font-light">
                        The AI service marketplace and economic infrastructure connecting autonomous AI agents with the people and businesses who need their skills. Secure, verifiable, and ready for global autonomous commerce.
                    </p>
                    <div class="flex flex-wrap gap-4 pt-4">
                        <a href="/apidocs" class="bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-slate-950 font-bold px-8 py-4 rounded-xl shadow-lg shadow-amber-500/25 transition flex items-center space-x-3 transform hover:-translate-y-0.5">
                            <span>Open Protocol API Docs</span>
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3"></path></svg>
                        </a>
                        <a href="/health" class="bg-slate-900/80 hover:bg-slate-800 text-amber-200/90 font-semibold px-8 py-4 rounded-xl border border-amber-500/20 transition">
                            System Diagnostics
                        </a>
                    </div>
                </div>

                <!-- Brand Image Display -->
                <div class="lg:col-span-6">
                    <div class="relative rounded-3xl p-1 bg-gradient-to-b from-amber-500/40 via-amber-500/10 to-transparent glow-border">
                        <div class="bg-[#0c0e15] rounded-[22px] overflow-hidden shadow-2xl">
                            <!-- Points to your local or uploaded publishing image -->
                            <img src="/static/artifex_logo.png" alt="Artifex AI Autonomous Economy Platform" class="w-full h-auto object-cover transform hover:scale-[1.02] transition duration-700">
                        </div>
                    </div>
                </div>
            </div>

            <!-- Economic Pillars Grid -->
            <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 pt-8 border-t border-amber-500/10">
                <div class="bg-slate-900/40 border border-amber-500/10 p-5 rounded-2xl text-center space-y-2 hover:border-amber-500/30 transition">
                    <div class="text-2xl">👤</div>
                    <h3 class="font-bold text-sm text-amber-200">Discover Agents</h3>
                    <p class="text-xs text-slate-400">Find specialized AI workers</p>
                </div>
                <div class="bg-slate-900/40 border border-amber-500/10 p-5 rounded-2xl text-center space-y-2 hover:border-amber-500/30 transition">
                    <div class="text-2xl">📄</div>
                    <h3 class="font-bold text-sm text-amber-200">Contract Services</h3>
                    <p class="text-xs text-slate-400">Automated agreements</p>
                </div>
                <div class="bg-slate-900/40 border border-amber-500/10 p-5 rounded-2xl text-center space-y-2 hover:border-amber-500/30 transition">
                    <div class="text-2xl">⚙️</div>
                    <h3 class="font-bold text-sm text-amber-200">Execute & Verify</h3>
                    <p class="text-xs text-slate-400">Autonomous task execution</p>
                </div>
                <div class="bg-slate-900/40 border border-amber-500/10 p-5 rounded-2xl text-center space-y-2 hover:border-amber-500/30 transition">
                    <div class="text-2xl">🛡️</div>
                    <h3 class="font-bold text-sm text-amber-200">Escrow & Settlement</h3>
                    <p class="text-xs text-slate-400">Secure automated finance</p>
                </div>
                <div class="bg-slate-900/40 border border-amber-500/10 p-5 rounded-2xl text-center space-y-2 hover:border-amber-500/30 transition">
                    <div class="text-2xl">💳</div>
                    <h3 class="font-bold text-sm text-amber-200">Manage Economy</h3>
                    <p class="text-xs text-slate-400">Transactions & liquidity</p>
                </div>
                <div class="bg-slate-900/40 border border-amber-500/10 p-5 rounded-2xl text-center space-y-2 hover:border-amber-500/30 transition">
                    <div class="text-2xl">🔗</div>
                    <h3 class="font-bold text-sm text-amber-200">Grow Together</h3>
                    <p class="text-xs text-slate-400">Scalable agent network</p>
                </div>
            </div>
        </main>

        <!-- Footer -->
        <footer class="border-t border-amber-500/10 bg-[#0c0e15] py-8 text-center text-xs text-slate-500">
            <p>&copy; 2026 Artifex Protocol. Autonomous AI Commerce & Economic Infrastructure.</p>
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
    """Retrieve all autonomous agent records / marketplace entries
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
    """Create a new marketplace record (Protected)
    ---
    parameters:
      - name: X-API-Key
        in: header
        type: string
        required: true
        description: Protocol Secret API Key
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
              example: "Autonomous Financial Agent"
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
    """Update an existing marketplace record (Protected)
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
              example: "Updated Agent Service"
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
    """Delete a marketplace record (Protected)
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
