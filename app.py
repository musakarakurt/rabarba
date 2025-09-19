import os
import json
from flask import Flask, redirect, request, session, url_for
import spotipy
from spotipy.oauth2 import SpotifyOAuth

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey")

# Spotify ayarları
CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI")
SCOPE = "user-read-email playlist-modify-private playlist-modify-public"
SHOW_ID = "40ORgVQqJWPQGRMUXmL67y"  # Rabarba podcast ID

# Konuk filtresi
GUESTS = [
    "Nuri Çetin",
    "Kemal Ayça",
    "İlker Gümüşoluk",
    "Anlatan Adam",
    "Anlatanadam",
    "Alper Çelik",
    "Ömür Okumuş",
    "Erman Arıcasoy",
]

QUEUE_FILE = "queue.json"


# ---------- Yardımcı Fonksiyonlar ----------
def load_queue():
    if not os.path.exists(QUEUE_FILE):
        return []
    with open(QUEUE_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def save_queue(data):
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_spotify_client():
    if "token_info" not in session:
        return None
    token_info = session["token_info"]
    return spotipy.Spotify(auth=token_info["access_token"])


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


def is_guest_in_title(title):
    title_lower = title.lower()
    return any(g.lower() in title_lower for g in GUESTS)


# ---------- Rotalar ----------
@app.route("/")
def index():
    if "token_info" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("view_queue"))


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
    token_info = sp_oauth.get_access_token(code, as_dict=True)
    session["token_info"] = token_info
    return redirect(url_for("index"))


@app.route("/load_podcast")
def load_podcast():
    sp = get_spotify_client()
    if not sp:
        return redirect(url_for("login"))

    episodes = fetch_all_episodes(sp)
    queue = load_queue()

    existing_ids = {ep["id"] for ep in queue}
    new_eps = []

    for ep in episodes:
        name = ep.get("name", "")
        if is_guest_in_title(name) and ep["id"] not in existing_ids:
            new_ep = {
                "id": ep["id"],
                "name": name,
                "release_date": ep.get("release_date", ""),
                "uri": ep.get("uri", ""),
                "played": False,
            }
            queue.append(new_ep)
            new_eps.append(new_ep)

    save_queue(queue)
    return {"queued": len(new_eps), "total": len(queue)}


@app.route("/view_queue")
def view_queue():
    queue = load_queue()
    html = "<h1>Podcast Queue</h1><ul>"
    for ep in queue:
        status = "Played" if ep.get("played") else "Not Played"
        html += f"<li>{ep['name']} ({ep['release_date']}) - {status}</li>"
    html += "</ul>"
    return html


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
