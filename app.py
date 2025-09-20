import os
import json
import re
from flask import Flask, redirect, request, session, url_for
import spotipy
from spotipy.oauth2 import SpotifyOAuth

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecret")
app.config["SESSION_COOKIE_NAME"] = "spotify-login-session"

# Spotify API credentials
CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("RENDER_BASE_URL", "http://localhost:5000") + "/callback"
SCOPE = "user-read-email"

# Show ID
SHOW_ID = "40ORgVQqJWPQGRMUXmL67y"

# Allowed guests (only these will be included)
ALLOWED_GUESTS = [
    "Nuri Çetin",
    "Kemal Ayça",
    "İlker Gümüşoluk",
    "Anlatan Adam",
    "Anlatanadam",
    "Alper Çelik",
    "Ömür Okumuş",
    "Erman Arıcasoy"
]

# File to store queue
QUEUE_FILE = "queue.json"


def get_spotify_client():
    return spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
            redirect_uri=REDIRECT_URI,
            scope=SCOPE
        )
    )


def normalize_title(title: str) -> str:
    """
    Düzenlenmiş başlık: A/B bölümlerinde A önce gelir.
    """
    match = re.search(r"(0\d+)([AB]?)", title)
    if not match:
        return title
    number = match.group(1)
    suffix = match.group(2) or "A"
    return f"{number}{suffix}"


def load_podcast():
    sp = get_spotify_client()
    results = sp.show_episodes(SHOW_ID, limit=50)
    episodes = results.get("items", [])

    while results.get("next"):
        results = sp.next(results)
        episodes.extend(results.get("items", []))

    # Filtre: sadece allowed guest olanlar
    filtered = []
    for ep in episodes:
        title = ep.get("name", "")
        if any(guest.lower() in title.lower() for guest in ALLOWED_GUESTS):
            filtered.append({
                "id": ep.get("id"),
                "name": ep.get("name"),
                "release_date": ep.get("release_date")
            })

    # Sıralama: önce tarih, sonra A/B
    filtered.sort(key=lambda e: (e["release_date"], normalize_title(e["name"])))

    # Ayır: unplayed vs choosen
    unplayed = filtered[:len(filtered)//2]
    choosen = filtered[len(filtered)//2:]

    queue_data = {"unplayed": unplayed, "choosen": choosen}

    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue_data, f, indent=2, ensure_ascii=False)

    return queue_data


@app.route("/")
def index():
    return """
    <h2>Spotify Podcast Manager</h2>
    <ul>
        <li><a href='/login'>Login</a></li>
        <li><a href='/load_podcast'>Load Podcast</a></li>
        <li><a href='/view_queue'>View Queue</a></li>
        <li><a href='/sync'>Synchronize</a></li>
    </ul>
    """


@app.route("/login")
def login():
    sp_oauth = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE
    )
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)


@app.route("/callback")
def callback():
    sp_oauth = SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE
    )
    session.clear()
    code = request.args.get("code")
    token_info = sp_oauth.get_access_token(code)
    session["token_info"] = token_info
    return redirect(url_for("index"))


@app.route("/load_podcast")
def load_podcast_route():
    try:
        queue_data = load_podcast()
        return {"queued": len(queue_data["unplayed"]) + len(queue_data["choosen"]),
                "total": len(queue_data["unplayed"]) + len(queue_data["choosen"])}
    except Exception as e:
        return {"error": str(e)}


@app.route("/view_queue")
def view_queue():
    try:
        if not os.path.exists(QUEUE_FILE):
            return {"error": "queue.json bulunamadı"}
        with open(QUEUE_FILE, "r", encoding="utf-8") as f:
            queue_data = json.load(f)
        return queue_data
    except Exception as e:
        return {"error": str(e)}


@app.route("/sync")
def sync():
    return {"status": "Sync completed"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
