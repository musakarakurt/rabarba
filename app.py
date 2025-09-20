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
SHOW_ID = "40ORgVQqJWPQGRMUXmL67y"  # Rabarba podcast ID

SCOPE = "user-read-email playlist-modify-public playlist-modify-private"

# JSON dosyası
QUEUE_FILE = "queue.json"

# Sadece senin verdiğin konuklar
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

# ---- Yardımcı Fonksiyonlar ----
def get_spotify():
    return spotipy.Spotify(auth=session.get("token_info")["access_token"])


def save_queue(episodes):
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(episodes, f, ensure_ascii=False, indent=2)


def load_queue():
    if not os.path.exists(QUEUE_FILE):
        return []
    with open(QUEUE_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


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


def filter_and_sort(episodes):
    filtered = []
    for ep in episodes:
        title = ep.get("name", "")
        if any(guest.lower() in title.lower() for guest in ALLOWED_GUESTS):
            filtered.append(ep)

    def ep_key(ep):
        match = re.search(r"(\d+)", ep.get("name", ""))
        num = int(match.group(1)) if match else 0
        is_b = " B" in ep.get("name", "").upper()
        return (num, 1 if is_b else 0)

    return sorted(filtered, key=ep_key)


# ---- Routes ----
@app.route("/")
def index():
    if "token_info" not in session:
        return redirect(url_for("login"))
    return """
    <h1>Logged in</h1>
    <a href='/load_podcast'>Load Podcast</a><br>
    <a href='/view_queue'>View Queue</a><br>
    <a href='/sync'>Synchronize</a>
    """


@app.route("/login")
def login():
    sp_oauth = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
    )
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)


@app.route("/callback")
def callback():
    sp_oauth = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
    )
    code = request.args.get("code")
    token_info = sp_oauth.get_access_token(code)
    session["token_info"] = token_info
    return redirect(url_for("index"))


@app.route("/load_podcast")
def load_podcast():
    try:
        sp = get_spotify()
        episodes = fetch_all_episodes(sp)
        episodes = filter_and_sort(episodes)
        save_queue(episodes)
        return {"queued": len(episodes), "total": len(episodes)}
    except Exception as e:
        return {"error": str(e)}


@app.route("/view_queue")
def view_queue():
    queue = load_queue()
    if not queue:
        return "Queue boş görünüyor!"
    out = ["<h1>Podcast Queue</h1>"]
    for ep in queue:
        out.append(f"{ep.get('name')} ({ep.get('release_date')})")
    return "<br>".join(out)


@app.route("/sync")
def sync():
    queue = load_queue()
    if not queue:
        return "Queue boş!"
    # Burada playlist senkronizasyonu yapılabilir (Spotify API ile).
    return f"{len(queue)} bölüm senkronize edilecek."


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
