import os
import re
import tempfile
from flask import Flask, request, send_file, jsonify, after_this_request
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return response

@app.route("/api/download", methods=["POST", "GET", "OPTIONS"])
def download():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        url = data.get("url", "").strip()
        quality = data.get("quality", "best").lower()
    else:
        url = request.args.get("url", "").strip()
        quality = request.args.get("quality", "720p").lower()

    if not url:
        return jsonify({"error": "No URL"}), 400

    tmp_dir = tempfile.mkdtemp()

    ydl_opts = {
        "outtmpl": os.path.join(tmp_dir, "%(title).80s.%(ext)s"),
        "format": "best[ext=mp4]/best",
        "noplaylist": True,
        "quiet": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        files = os.listdir(tmp_dir)
        if not files:
            return jsonify({"error": "No file produced"}), 500
        filepath = os.path.join(tmp_dir, files[0])
        @after_this_request
        def cleanup(response):
            try:
                os.remove(filepath)
                os.rmdir(tmp_dir)
            except:
                pass
            return response
        return send_file(filepath, as_attachment=True, download_name=files[0])
    except Exception as e:
        return jsonify({"error": str(e)[:300]}), 400

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
