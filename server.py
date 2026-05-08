"""
VidSnatch Backend — server.py
────────────────────────────────────────────────────
Run:  python server.py
Deps: pip install flask flask-cors yt-dlp
Also: install ffmpeg (brew install ffmpeg / apt install ffmpeg)
"""

from flask import Flask, request, send_file, jsonify, after_this_request
from flask_cors import CORS
import yt_dlp
import tempfile
import os
import re

app = Flask(_name_)
CORS(app)  # allow requests from your frontend

# ── Optional: simple API key for premium users ──────────────
PREMIUM_KEY = "your-secret-premium-key"  # set a real key, pass from frontend header

def is_premium(req):
    return req.headers.get("X-Premium-Key") == PREMIUM_KEY


def get_format(quality: str, premium: bool) -> dict:
    """Return yt-dlp options for a given quality string."""
    postprocessors = []

    if quality == "audio":
        fmt = "bestaudio/best"
        postprocessors = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "320" if premium else "192",
        }]
    elif quality == "best":
        fmt = "bestvideo+bestaudio/best"
    elif quality in ("4k", "2160p"):
        if not premium:
            return None  # locked
        fmt = "bestvideo[height<=2160]+bestaudio/best"
    elif quality == "8k":
        if not premium:
            return None
        fmt = "bestvideo[height<=4320]+bestaudio/best"
    elif quality == "1080p":
        fmt = "bestvideo[height<=1080]+bestaudio/best"
    elif quality == "720p":
        fmt = "bestvideo[height<=720]+bestaudio/best"
    elif quality == "480p":
        fmt = "bestvideo[height<=480]+bestaudio/best"
    else:
        fmt = "bestvideo+bestaudio/best"

    return {"format": fmt, "postprocessors": postprocessors}


@app.route("/api/download", methods=["POST", "GET"])
def download():
    # Support both POST JSON and GET query params
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        url = data.get("url", "").strip()
        quality = data.get("quality", "best").lower()
    else:
        url = request.args.get("url", "").strip()
        quality = request.args.get("quality", "best").lower()

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    # Basic URL sanity check
    if not re.match(r"https?://", url):
        return jsonify({"error": "Invalid URL"}), 400

    premium = is_premium(request)
    fmt_opts = get_format(quality, premium)

    if fmt_opts is None:
        return jsonify({"error": "This quality requires a Premium plan."}), 403

    tmp_dir = tempfile.mkdtemp()

    ydl_opts = {
        "outtmpl": os.path.join(tmp_dir, "%(title).80s.%(ext)s"),
        "format": fmt_opts["format"],
        "postprocessors": fmt_opts.get("postprocessors", []),
        "merge_output_format": "mp4",
        "noplaylist": True,          # single video only
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        files = os.listdir(tmp_dir)
        if not files:
            return jsonify({"error": "Download failed — no file produced."}), 500

        filepath = os.path.join(tmp_dir, files[0])
        filename = files[0]

        # Cleanup after sending
        @after_this_request
        def cleanup(response):
            try:
                os.remove(filepath)
                os.rmdir(tmp_dir)
            except Exception:
                pass
            return response

        return send_file(
            filepath,
            as_attachment=True,
            download_name=filename,
        )

    except yt_dlp.utils.DownloadError as e:
        return jsonify({"error": f"Download error: {str(e)[:200]}"}), 400
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)[:200]}"}), 500


@app.route("/api/info", methods=["POST"])
def video_info():
    """Return metadata (title, thumbnail, duration) without downloading."""
    data = request.get_json(silent=True) or {}
    url = data.get("url", "").strip()

    if not url:
        return jsonify({"error": "No URL"}), 400

    try:
        with yt_dlp.YoutubeDL({"quiet": True, "skip_download": True}) as ydl:
            info = ydl.extract_info(url, download=False)
            return jsonify({
                "title": info.get("title"),
                "thumbnail": info.get("thumbnail"),
                "duration": info.get("duration"),
                "uploader": info.get("uploader"),
                "platform": info.get("extractor_key"),
            })
    except Exception as e:
        return jsonify({"error": str(e)[:200]}), 400


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if _name_ == "_main_":
    print("═" * 50)
    print("  VidSnatch Backend running at http://localhost:5000")
    print("═" * 50)
   import os
app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
