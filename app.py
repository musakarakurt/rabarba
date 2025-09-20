import os
import json
from flask import Flask, redirect, request, session, url_for, jsonify
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Flask app
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "supersecret")

# Spotify credentials
SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
SPOTIPY_REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI")

SHOW_ID = "40ORgVQqJWPQGRMUXmL67y"  # Rabarba Show ID

scope = "user-read-email"

# --- Spotify client ---
def get_spotify_client():
    token_info = session.get("token_info", None)
    if not token_info:
        return None
    return spotipy.Spotify(auth=token_info["access_token"])

# --- Fetch episodes ---
def fetch_all_episodes(sp):
    all_eps = []
    offset = 0
    limit = 50
    while True:
        res = sp.show_episodes(SHOW_ID, limit=limit, offset=offset)
        items = res.get("items", []) or []
        items = [it for it in items if isinstance(it, dict)]
        all_eps.extend(items)
        if len(items) < limit:
            break
        offset += limit
    return all_eps

# --- Routes ---
@app.route("/")
def index():
    return '<a href="/login">Log In with Spotify</a><br><a href="/view_queue">View Queue</a><br><a href="/load_podcast">Load Podcast</a>'

@app.route("/login")
def login():
    sp_oauth = SpotifyOAuth(
        SPOTIPY_CLIENT_ID,
        SPOTIPY_CLIENT_SECRET,
        SPOTIPY_REDIRECT_URI,
        scope=scope
    )
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route("/callback")
def callback():
    sp_oauth = SpotifyOAuth(
        SPOTIPY_CLIENT_ID,
        SPOTIPY_CLIENT_SECRET,
        SPOTIPY_REDIRECT_URI,
        scope=scope
    )
    code = request.args.get("code")
    token_info = sp_oauth.get_access_token(code)
    session["token_info"] = token_info
    return redirect(url_for("index"))

@app.route("/load_podcast")
def load_podcast():
    try:
        sp = get_spotify_client()
        if not sp:
            return redirect(url_for("login"))

        episodes = fetch_all_episodes(sp)
        if not episodes:
            return jsonify({"error": "No episodes fetched"})

        with open("queue.json", "w", encoding="utf-8") as f:
            json.dump(episodes, f, ensure_ascii=False, indent=2)

        return jsonify({"queued": len(episodes), "total": len(episodes)})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/view_queue")
def view_queue():
    try:
        if not os.path.exists("queue.json"):
            return "queue.json boş görünüyor!"
        with open("queue.json", "r", encoding="utf-8") as f:
            queue = json.load(f)
        return jsonify(queue)
    except Exception as e:
        return f"Hata: {e}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
