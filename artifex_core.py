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

template = {
    "swagger": "2.0",
    "info": {
        "title": "Artifex Protocol API",
        "description": "Secure autonomous AI commerce & economic infrastructure. Authenticated via protocol headers.",
        "version": "1.0.0",
        "contact": {
            "name": "Artifex Support",
            "url": "https://artifex-core.onrender.com"
        }
    },
    "host": "artifex-core.onrender.com",
    "basePath": "/",
    "schemes": ["https", "http"]
}

swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec_1',
            "route": '/apispec_1.json',
            "rule_filter": lambda rule: True,
            "model_filter": lambda rule: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": False
}

swagger = Swagger(app, template=template, config=swagger_config)

API_KEY = os.environ.get("API_KEY", "artifex-secret-key-123")

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_key = request.headers.get('X-API-Key')
        if user_key and user_key == API_KEY:
            return f(*args, **kwargs)
        return jsonify({"error": "Unauthorized: Missing or valid API key required"}), 401
    return decorated_function

class Record(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), default="Autonomous AI Agent Worker")
    status = db.Column(db.String(50), default="Active")

    def to_dict(self):
        return {"id": self.id, "name": self.name, "description": self.description, "status": self.status}

with app.app_context():
    db.create_all()
    # Seed initial records if empty so the registry isn't blank
    if Record.query.count() == 0:
        default_agents = [
            Record(name="Autonomous Financial Settlement Agent", description="Manages automated cross-chain liquidity and escrow disbursement.", status="Online"),
            Record(name="Smart Contract Auditor AI", description="Real-time vulnerability scanning and formal verification of agent protocols.", status="Online"),
            Record(name="Decentralized Task Coordinator", description="Matches human economic requests with specialized autonomous agent worker swarms.", status="Standby"),
            Record(name="Autonomous Legal & Compliance Agent", description="Generates dynamic legal service micro-contracts and verifies protocol compliance.", status="Online")
        ]
        db.session.add_all(default_agents)
        db.session.commit()

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory('static', filename)

@app.route('/', methods=['GET'])
def home():
    """Artifex Ecosystem Home"""
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
            body { font-family: 'Inter', sans-serif; background-color: #090a0f; }
            .glow-border { box-shadow: 0 0 35px -5px rgba(245, 158, 11, 0.15); }
        </style>
    </head>
    <body class="text-slate-100 min-h-screen flex flex-col justify-between selection:bg-amber-500 selection:text-slate-950">
        
        <!-- Navbar -->
        <header class="border-b border-amber-500/10 bg-[#0c0e15]/90 backdrop-blur-md sticky top-0 z-50">
            <div class="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
                <div class="flex items-center space-x-3">
                    <div class="h-3 w-3 rounded-full bg-amber-500 animate-pulse"></div>
                    <span class="font-extrabold text-xl tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-amber-200 via-amber-400 to-orange-500">ARTIFEX</span>
                </div>
                <nav class="flex items-center space-x-6">
                    <a href="/" class="text-sm font-medium text-amber-400 transition">Home</a>
                    <a href="/apidocs" class="text-sm font-medium text-amber-200/80 hover:text-amber-400 transition">API Documentation</a>
                    <a href="/registry" class="text-sm font-medium text-amber-200/80 hover:text-amber-400 transition">Marketplace Registry</a>
                    <a href="https://github.com" target="_blank" class="bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 text-sm font-semibold px-5 py-2.5 rounded-xl transition border border-amber-500/30">Protocol GitHub</a>
                </nav>
            </div>
        </header>

        <!-- Hero Section -->
        <main class="max-w-7xl mx-auto px-6 py-16 space-y-16">
            <div class="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
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
                            <span>Explore Protocol API Docs</span>
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" stroke-width="2.5" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3"></path></svg>
                        </a>
                        <a href="/registry" class="bg-slate-900/80 hover:bg-slate-800 text-amber-200/90 font-semibold px-8 py-4 rounded-xl border border-amber-500/20 transition flex items-center space-x-2">
                            <span>View Agent Registry</span>
                        </a>
                    </div>
                </div>

                <div class="lg:col-span-6">
                    <div class="relative rounded-3xl p-1 bg-gradient-to-b from-amber-500/40 via-amber-500/10 to-transparent glow-border">
                        <div class="bg-[#0c0e15] rounded-[22px] overflow-hidden shadow-2xl flex items-center justify-center min-h-[320px]">
                            <img src="/static/20260918_194719.jpg" alt="Artifex AI Autonomous Economy Platform" class="w-full h-auto object-cover transform hover:scale-[1.02] transition duration-700" onerror="this.onerror=null; this.src='/static/artifex_logo.png';">
                        </div>
                    </div>
                </div>
            </div>

            <!-- Economic Pillars (Interactive) -->
            <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 pt-8 border-t border-amber-500/10">
                <a href="/registry" class="bg-slate-900/40 border border-amber-500/10 p-5 rounded-2xl text-center space-y-2 hover:border-amber-500/40 hover:bg-slate-900 transition group block">
                    <div class="text-2xl group-hover:scale-110 transition">👤</div>
                    <h3 class="font-bold text-sm text-amber-200">Discover Agents</h3>
                    <p class="text-xs text-slate-400">Find specialized AI workers</p>
                </a>
                <a href="/apidocs" class="bg-slate-900/40 border border-amber-500/10 p-5 rounded-2xl text-center space-y-2 hover:border-amber-500/40 hover:bg-slate-900 transition group block">
                    <div class="text-2xl group-hover:scale-110 transition">📄</div>
                    <h3 class="font-bold text-sm text-amber-200">Contract Services</h3>
                    <p class="text-xs text-slate-400">Automated agreements</p>
                </a>
                <a href="/registry" class="bg-slate-900/40 border border-amber-500/10 p-5 rounded-2xl text-center space-y-2 hover:border-amber-500/40 hover:bg-slate-900 transition group block">
                    <div class="text-2xl group-hover:scale-110 transition">⚙️</div>
                    <h3 class="font-bold text-sm text-amber-200">Execute & Verify</h3>
                    <p class="text-xs text-slate-400">Autonomous task execution</p>
                </a>
                <a href="/apidocs" class="bg-slate-900/40 border border-amber-500/10 p-5 rounded-2xl text-center space-y-2 hover:border-amber-500/40 hover:bg-slate-900 transition group block">
                    <div class="text-2xl group-hover:scale-110 transition">🛡️</div>
                    <h3 class="font-bold text-sm text-amber-200">Escrow & Settlement</h3>
                    <p class="text-xs text-slate-400">Secure automated finance</p>
                </a>
                <a href="/registry" class="bg-slate-900/40 border border-amber-500/10 p-5 rounded-2xl text-center space-y-2 hover:border-amber-500/40 hover:bg-slate-900 transition group block">
                    <div class="text-2xl group-hover:scale-110 transition">💳</div>
                    <h3 class="font-bold text-sm text-amber-200">Manage Economy</h3>
                    <p class="text-xs text-slate-400">Transactions & liquidity</p>
                </a>
                <a href="https://github.com" target="_blank" class="bg-slate-900/40 border border-amber-500/10 p-5 rounded-2xl text-center space-y-2 hover:border-amber-500/40 hover:bg-slate-900 transition group block">
                    <div class="text-2xl group-hover:scale-110 transition">🔗</div>
                    <h3 class="font-bold text-sm text-amber-200">Grow Together</h3>
                    <p class="text-xs text-slate-400">Scalable agent network</p>
                </a>
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

@app.route('/apidocs', methods=['GET'])
def apidocs():
    """Custom Embedded API Documentation Page matching exact site layout"""
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Artifex | Protocol API Documentation</title>
        <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
        <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
        <style>
            body { font-family: 'Inter', sans-serif; background-color: #090a0f; }
            .swagger-ui { color: #f8fafc; }
            .swagger-ui .info h1, .swagger-ui .info h2, .swagger-ui .info p { color: #f8fafc !important; }
            .swagger-ui .info a { color: #f59e0b !important; }
            .swagger-ui .scheme-container { background: #0c0e15 !important; border-radius: 12px; box-shadow: none; border: 1px solid rgba(245, 158, 11, 0.1); }
            .swagger-ui .opblock { background: #0c0e15 !important; border: 1px solid rgba(245, 158, 11, 0.2) !important; border-radius: 12px !important; }
            .swagger-ui .opblock .opblock-summary-path { color: #f1f5f9 !important; }
            .swagger-ui .btn.authorize { background-color: transparent !important; border-color: #f59e0b !important; color: #f59e0b !important; }
            .swagger-ui select, .swagger-ui input[type=text] { background: #0c0e15 !important; color: white !important; border: 1px solid rgba(245, 158, 11, 0.3) !important; }
        </style>
    </head>
    <body class="text-slate-100 min-h-screen flex flex-col justify-between">
        
        <!-- Navbar -->
        <header class="border-b border-amber-500/10 bg-[#0c0e15]/90 backdrop-blur-md sticky top-0 z-50">
            <div class="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
                <div class="flex items-center space-x-3">
                    <div class="h-3 w-3 rounded-full bg-amber-500 animate-pulse"></div>
                    <span class="font-extrabold text-xl tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-amber-200 via-amber-400 to-orange-500">ARTIFEX</span>
                </div>
                <nav class="flex items-center space-x-6">
                    <a href="/" class="text-sm font-medium text-amber-200/80 hover:text-amber-400 transition">Home</a>
                    <a href="/apidocs" class="text-sm font-medium text-amber-400 transition">API Documentation</a>
                    <a href="/registry" class="text-sm font-medium text-amber-200/80 hover:text-amber-400 transition">Marketplace Registry</a>
                    <a href="https://github.com" target="_blank" class="bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 text-sm font-semibold px-5 py-2.5 rounded-xl transition border border-amber-500/30">Protocol GitHub</a>
                </nav>
            </div>
        </header>

        <!-- Main Content Container with Embedded Swagger -->
        <main class="max-w-7xl mx-auto px-6 py-12 w-full flex-grow space-y-8">
            <div class="space-y-2">
                <div class="inline-flex items-center space-x-2 bg-amber-500/10 border border-amber-500/30 px-4 py-1.5 rounded-full text-amber-400 text-xs font-bold uppercase tracking-widest">
                    <span>Developer Protocol</span>
                </div>
                <h1 class="text-3xl font-black text-white">API Documentation & Gateway</h1>
                <p class="text-slate-400 text-sm">Interactive endpoints, schemas, and authorization protocols for autonomous AI agents and developers.</p>
            </div>

            <div class="bg-[#0c0e15] border border-amber-500/20 rounded-3xl p-6 shadow-2xl">
                <div id="swagger-ui"></div>
            </div>
        </main>

        <!-- Footer -->
        <footer class="border-t border-amber-500/10 bg-[#0c0e15] py-8 text-center text-xs text-slate-500">
            <p>&copy; 2026 Artifex Protocol. Autonomous AI Commerce & Economic Infrastructure.</p>
        </footer>

        <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js" crossorigin></script>
        <script>
            window.onload = () => {
                window.ui = SwaggerUIBundle({
                    url: '/apispec_1.json',
                    dom_id: '#swagger-ui',
                    presets: [
                        SwaggerUIBundle.presets.apis,
                        SwaggerUIBundle.SwaggerUIStandalonePreset
                    ],
                    layout: "BaseLayout"
                });
            };
        </script>
    </body>
    </html>
    """
    return render_template_string(html_template), 200

@app.route('/health', methods=['GET'])
@app.route('/health/external', methods=['GET'])
def health_external():
    """Internal System Health Check"""
    return jsonify({"status": "ok"}), 200

@app.route('/registry', methods=['GET'])
def registry_ui():
    """Human-facing Agent Registry dashboard UI"""
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Artifex | Autonomous Agent Registry</title>
        <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
        <style>
            body { font-family: 'Inter', sans-serif; background-color: #090a0f; }
        </style>
    </head>
    <body class="text-slate-100 min-h-screen flex flex-col justify-between selection:bg-amber-500 selection:text-slate-950">
        
        <!-- Navbar -->
        <header class="border-b border-amber-500/10 bg-[#0c0e15]/90 backdrop-blur-md sticky top-0 z-50">
            <div class="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
                <div class="flex items-center space-x-3">
                    <div class="h-3 w-3 rounded-full bg-amber-500 animate-pulse"></div>
                    <span class="font-extrabold text-xl tracking-wider text-transparent bg-clip-text bg-gradient-to-r from-amber-200 via-amber-400 to-orange-500">ARTIFEX</span>
                </div>
                <nav class="flex items-center space-x-6">
                    <a href="/" class="text-sm font-medium text-amber-200/80 hover:text-amber-400 transition">Home</a>
                    <a href="/apidocs" class="text-sm font-medium text-amber-200/80 hover:text-amber-400 transition">API Documentation</a>
                    <a href="/registry" class="text-sm font-medium text-amber-400 transition">Marketplace Registry</a>
                    <a href="https://github.com" target="_blank" class="bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 text-sm font-semibold px-5 py-2.5 rounded-xl transition border border-amber-500/30">Protocol GitHub</a>
                </nav>
            </div>
        </header>

        <!-- Main Registry Section -->
        <main class="max-w-7xl mx-auto px-6 py-12 w-full flex-grow space-y-8">
            <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div class="space-y-2">
                    <div class="inline-flex items-center space-x-2 bg-amber-500/10 border border-amber-500/30 px-4 py-1.5 rounded-full text-amber-400 text-xs font-bold uppercase tracking-widest">
                        <span>Economic Marketplace</span>
                    </div>
                    <h1 class="text-3xl font-black text-white">Autonomous Agent Registry</h1>
                    <p class="text-slate-400 text-sm">Live directory of active autonomous economic nodes currently deployed on the Artifex infrastructure.</p>
                </div>
                <div>
                    <button onclick="openModal()" class="bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-slate-950 font-bold px-6 py-3 rounded-xl shadow-lg shadow-amber-500/20 transition flex items-center space-x-2">
                        <span>+ Register New Agent</span>
                    </button>
                </div>
            </div>

            <!-- Agents Grid -->
            <div id="agents-grid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                <div class="text-slate-500 text-sm py-12 text-center col-span-full">Loading agent network nodes...</div>
            </div>
        </main>

        <!-- Modal for registering new agent -->
        <div id="agent-modal" class="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 hidden flex items-center justify-center p-4">
            <div class="bg-[#0c0e15] border border-amber-500/30 rounded-3xl p-8 max-w-md w-full space-y-6 shadow-2xl">
                <div class="flex justify-between items-center">
                    <h3 class="text-xl font-bold text-white">Register Autonomous Agent</h3>
                    <button onclick="closeModal()" class="text-slate-400 hover:text-white text-xl">&times;</button>
                </div>
                <form id="agent-form" onsubmit="submitAgent(event)" class="space-y-4">
                    <div>
                        <label class="block text-xs font-semibold text-amber-200/80 uppercase mb-2">Agent Name</label>
                        <input type="text" id="agent-name" required placeholder="e.g. Autonomous Supply Chain Coordinator" class="w-full bg-slate-900 border border-amber-500/30 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-amber-400">
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-amber-200/80 uppercase mb-2">Capabilities / Description</label>
                        <textarea id="agent-desc" rows="3" required placeholder="Describe what this AI worker accomplishes..." class="w-full bg-slate-900 border border-amber-500/30 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-amber-400"></textarea>
                    </div>
                    <div>
                        <label class="block text-xs font-semibold text-amber-200/80 uppercase mb-2">Protocol Secret API Key</label>
                        <input type="password" id="api-key-input" required placeholder="artifex-secret-key-123" class="w-full bg-slate-900 border border-amber-500/30 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-amber-400">
                    </div>
                    <div class="flex justify-end space-x-3 pt-2">
                        <button type="button" onclick="closeModal()" class="px-5 py-2.5 rounded-xl text-slate-400 hover:text-white text-sm font-semibold">Cancel</button>
                        <button type="submit" class="bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold px-6 py-2.5 rounded-xl text-sm transition">Deploy Node</button>
                    </div>
                </form>
            </div>
        </div>

        <!-- Footer -->
        <footer class="border-t border-amber-500/10 bg-[#0c0e15] py-8 text-center text-xs text-slate-500">
            <p>&copy; 2026 Artifex Protocol. Autonomous AI Commerce & Economic Infrastructure.</p>
        </footer>

        <script>
            async function fetchAgents() {
                try {
                    const res = await fetch('/records');
                    const data = await res.json();
                    const grid = document.getElementById('agents-grid');
                    if (data.length === 0) {
                        grid.innerHTML = '<div class="text-slate-500 text-sm py-12 text-center col-span-full">No active agents registered in the network.</div>';
                        return;
                    }
                    grid.innerHTML = data.map(agent => `
                        <div class="bg-[#0c0e15] border border-amber-500/20 rounded-2xl p-6 space-y-4 hover:border-amber-500/40 transition shadow-lg flex flex-col justify-between">
                            <div class="space-y-2">
                                <div class="flex items-center justify-between">
                                    <span class="text-xs px-3 py-1 bg-amber-500/10 border border-amber-500/30 text-amber-400 rounded-full font-bold">Node #${agent.id}</span>
                                    <span class="flex items-center space-x-1.5 text-xs text-emerald-400 font-medium">
                                        <span class="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
                                        <span>${agent.status || 'Active'}</span>
                                    </span>
                                </div>
                                <h3 class="text-lg font-bold text-white pt-2">${agent.name}</h3>
                                <p class="text-slate-400 text-xs leading-relaxed">${agent.description || 'Autonomous AI Agent Worker'}</p>
                            </div>
                            <div class="pt-4 border-t border-amber-500/10 flex justify-between items-center text-xs text-amber-200/70">
                                <span>Verified Protocol Node</span>
                                <span class="font-mono text-[10px] bg-slate-900 px-2 py-1 rounded border border-amber-500/10">SECURE-TLS</span>
                            </div>
                        </div>
                    `).join('');
                } catch (err) {
                    console.error('Failed to load agents:', err);
                }
            }

            function openModal() {
                document.getElementById('agent-modal').classList.remove('hidden');
            }

            function closeModal() {
                document.getElementById('agent-modal').classList.add('hidden');
            }

            async function submitAgent(e) {
                e.preventDefault();
                const name = document.getElementById('agent-name').value;
                const description = document.getElementById('agent-desc').value;
                const apiKey = document.getElementById('api-key-input').value;

                try {
                    const res = await fetch('/records', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-API-Key': apiKey
                        },
                        body: JSON.stringify({ name, description })
                    });

                    if (res.ok) {
                        closeModal();
                        document.getElementById('agent-form').reset();
                        fetchAgents();
                    } else {
                        const errData = await res.json();
                        alert('Deployment failed: ' + (errData.error || 'Unauthorized API Key'));
                    }
                } catch (err) {
                    alert('Network error during deployment.');
                }
            }

            fetchAgents();
        </script>
    </body>
    </html>
    """
    return render_template_string(html_template), 200

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
            description:
              type: string
              example: "Manages liquidity escrow."
    responses:
      201:
        description: Record created successfully
      401:
        description: Unauthorized
    """
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({"error": "Invalid request, 'name' is required"}), 400
    
    new_record = Record(
        name=data['name'],
        description=data.get('description', 'Autonomous AI Agent Worker'),
        status="Online"
    )
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
    if 'description' in data:
        record.description = data['description']
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
