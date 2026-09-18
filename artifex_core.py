from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/health/external', methods=['GET'])
def health_external():
    return jsonify({"status": "healthy", "service": "artifex-core"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
