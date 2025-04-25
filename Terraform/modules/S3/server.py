from flask import Flask, request
import requests
app = Flask(__name__)
@app.route("/")
def home():
    return "SSRF Vulnerable App - Use /fetch?url=http://example.com"
# Vulnerable endpoint
@app.route("/fetch")
def fetch():
    target_url = request.args.get("url")
    if not target_url:
        return "URL parameter is required", 400
    try:
        response = requests.get(target_url)  # No validation, making it vulnerable
        return response.text
    except requests.exceptions.RequestException as e:
        return str(e), 500
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)