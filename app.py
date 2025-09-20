import os
import json
from flask import Flask, redirect, request, session, url_for, jsonify
import spotipy
from spotipy.oauth2 import SpotifyOAuth

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "dev_secret")

# Spotify API bilgileri
CLIENT_ID = os.environ.get("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.environ.get("SPOTIPY_CLIENT_SECRET")
REDIRECT_URI = os.environ.get("SPOTIPY_REDIRECT_URI")
SHOW_ID = "40ORgVQqJWPQGRMUXmL67y"

SCOPE = "user-library-read playlist-modify-public playlist-modify-private"

QUEUE_FILE = "queue.json"

ALLOWED_GUESTS = [
    "Nuri Çetin",
    "Kemal Ayça",
    "İlker Gümüşoluk",
    "Anlatan Adam",
    "Anlatanadam",
    "Alper Çelik",
    "Ömür Okumuş",
    "Erman Arıcasoy",
]

# ------------------------------------------------------------
# Yardımcı fonksiyonlar
# ------------------------------------------------------------
def get_spotify():
    return spotipy.Spotify(auth=session.get("token_info")["access_token"])

def save_queue(data):
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_queue():
    if not os.path.exists(QUEUE_FILE):
        return {"unplayed": [], "choosen": []}
    with open(QUEUE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def parse_episode_number(name):
    # Örn: "Mesut Süre ile RABARBA 0855 (Podcast Edit)"
    parts = name.split()
    for p in parts:
        if p.isdigit():
            return int(p)
    return 0

def fetch_all_episodes(sp):
    episodes = []
    offset = 0
    limit = 50
    while True:
        res = sp.show_episodes(trid, limit=limit, offset=offset)
if not res or "items" not in res:
    break
    episodes.extend(items)
    if len(items) < limit:
            break
    offset += limit
    
return episodes

def filter_and_sort(episodes):
    unplayed = []
    choosen = []

    for ep in episodes:
        name = ep.get("name", "")
        desc = ep.get("description", "")

        # Sadece ALLOWED_GUESTS listesinde olanları seç
        if any(guest.lower() in (name + desc).lower() for guest in ALLOWED_GUESTS):
            choosen.append(name)
        else:
            unplayed.append(name)

    # Sıralama: sayı + A/B mantığı
    def sort_key(title):
        num = parse_episode_number(title)
        suffix = 0 if "(A" in title or " A" in title else (1 if "(B" in title or " B" in title else 2)
        return (num, suffix)

    unplayed.sort(key=sort_key)
    choosen.sort(key=sort_key)

    return {"unplayed": unplayed, "choosen": choosen}

# ------------------------------------------------------------
# Routes
# ------------------------------------------------------------
@app.route("/")
def index():
    if "token_info" not in session:
        return '<a href="/login">Login with Spotify</a>'
    return """
        <h1>Logged in</h1>
        <ul>
          <li><a href="/load_podcast">Load Podcast</a></li>
          <li><a href="/view_queue">View Queue</a></li>
          <li><a href="/sync_unplayed">Synchronize (Unplayed)</a></li>
          <li><a href="/sync_playlist">Synchronize (Choosen)</a></li>
        </ul>
    """

@app.route("/login")
def login():
    sp_oauth = SpotifyOAuth(client_id=CLIENT_ID, client_secret=CLIENT_SECRET,
                            redirect_uri=REDIRECT_URI, scope=SCOPE)
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route("/callback")
def callback():
    sp_oauth = SpotifyOAuth(client_id=CLIENT_ID, client_secret=CLIENT_SECRET,
                            redirect_uri=REDIRECT_URI, scope=SCOPE)
    code = request.args.get("code")
    token_info = sp_oauth.get_access_token(code)
    session["token_info"] = token_info
    return redirect(url_for("index"))

@app.route("/load_podcast")
def load_podcast():
    try:
        sp = get_spotify()
        episodes = fetch_all_episodes(sp)
        filtered = filter_and_sort(episodes)
        save_queue(filtered)
        return jsonify({"queued": len(filtered["unplayed"]) + len(filtered["choosen"]),
                        "unplayed": len(filtered["unplayed"]),
                        "choosen": len(filtered["choosen"])})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route("/view_queue")
def view_queue():
    q = load_queue()
    if not q or (not q.get("unplayed") and not q.get("choosen")):
        return "Queue boş görünüyor!"
    return jsonify(q)

@app.route("/sync_unplayed")
def sync_unplayed():
    q = load_queue()
    return jsonify({"sync_unplayed": len(q.get("unplayed", []))})

@app.route("/sync_playlist")
def sync_playlist():
    q = load_queue()
    return jsonify({"sync_choosen": len(q.get("choosen", []))})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
