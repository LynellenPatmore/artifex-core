from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///artifex.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Record(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    def to_dict(self):
        return {"id": self.id, "name": self.name}

with app.app_context():
    db.create_all()

@app.route('/', methods=['GET'])
def home():
    return "Artifex Dashboard - Welcome to Artifex Core API", 200

@app.route('/health', methods=['GET'])
@app.route('/health/external', methods=['GET'])
def health_external():
    return jsonify({"status": "ok"}), 200

@app.route('/records', methods=['GET'])
def get_records():
    records = Record.query.all()
    return jsonify([r.to_dict() for r in records]), 200

@app.route('/records', methods=['POST'])
def add_record():
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({"error": "Invalid request, 'name' is required"}), 400
    
    new_record = Record(name=data['name'])
    db.session.add(new_record)
    db.session.commit()
    return jsonify(new_record.to_dict()), 201

@app.route('/records/<int:record_id>', methods=['PUT'])
def update_record(record_id):
    record = db.get_or_404(Record, record_id)
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({"error": "Invalid request, 'name' is required"}), 400
    
    record.name = data['name']
    db.session.commit()
    return jsonify(record.to_dict()), 200

@app.route('/records/<int:record_id>', methods=['DELETE'])
def delete_record(record_id):
    record = db.get_or_404(Record, record_id)
    db.session.delete(record)
    db.session.commit()
    return jsonify({"message": f"Record {record_id} deleted successfully"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
