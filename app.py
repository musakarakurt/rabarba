import os
import json
import re
from flask import Flask, redirect, request, session, url_for
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Flask app
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "supersecret")

# Spotify API credentials
CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI")
SHOW_ID = os.getenv("SHOW_ID")  # örn: 40ORgVQqJWPQGRMUXmL67y

# Guest filter list (sadece senin verdiğin isimler)
guests = [
    "Nuri Çetin",
    "Kemal Ayça",
    "İlker Gümüşoluk",
    "Anlatan Adam",
    "Anlatanadam",
    "Alper Çelik",
    "Ömür Okumuş",
    "Erman Arıcasoy"
]

# Queue file
QUEUE_FILE = "queue.json"

def load_queue():
    if not os.path.exists(QUEUE_FILE):
        return []
    try:
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_queue(queue):
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, indent=2, ensure_ascii=False)

def create_spotify_oauth():
    return SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope="user-read-playback-state playlist-modify-public playlist-modify-private"
    )

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

@app.route("/")
def index():
    if not session.get("token_info"):
        return redirect(url_for("login"))
    return """
    <h1>Logged in</h1>
    <a href='/load_podcast'>Load Podcast</a><br>
    <a href='/view_queue'>View Queue</a>
    """

@app.route("/login")
def login():
    sp_oauth = create_spotify_oauth()
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route("/callback")
def callback():
    sp_oauth = create_spotify_oauth()
    code = request.args.get("code")
    token_info = sp_oauth.get_access_token(code, as_dict=False)
    session["token_info"] = token_info
    return redirect(url_for("index"))

@app.route("/load_podcast")
def load_podcast():
    try:
        sp_oauth = create_spotify_oauth()
        token_info = session.get("token_info")
        if not token_info:
            return redirect(url_for("login"))

        sp = spotipy.Spotify(auth=token_info["access_token"])
        episodes = fetch_all_episodes(sp)

        queue = []
        for ep in episodes:
            title = ep.get("name") or ""
            match = re.search(r"(\d+)", title)
            num = int(match.group(1)) if match else 0

            desc = ep.get("description", "")
            if any(g.lower() in (title + desc).lower() for g in guests):
                queue.append({
                    "num": num,
                    "title": title,
                    "date": ep.get("release_date"),
                    "played": False
                })

        # Numara sıralaması (küçükten büyüğe)
        queue.sort(key=lambda x: x["num"])

        save_queue(queue)

        return {"queued": len(queue), "total": len(episodes)}
    except Exception as e:
        return {"error": str(e)}

@app.route("/view_queue")
def view_queue():
    try:
        queue = load_queue()
        if not queue:
            return "Queue boş görünüyor!"
        html = "<h1>Podcast Queue</h1><ul>"
        for ep in queue:
            html += f"<li>Rabarba {ep['num']}: {ep['title']} ({ep['date']}) - {'Played' if ep['played'] else 'Not Played'}</li>"
        html += "</ul>"
        return html
    except Exception as e:
        return f"Hata: {e}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
