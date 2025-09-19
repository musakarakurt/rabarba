import os
import json
from flask import Flask, redirect, request, session
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Flask uygulaması
app = Flask(_name_)
app.secret_key = os.getenv("FLASK_SECRET", "supersecret")

# Spotify API ayarları
CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI")
SHOW_ID = "40ORgVQqJWPQGRMUXmL67y"  # Rabarba show ID

SCOPE = "user-read-playback-state,user-modify-playback-state,playlist-modify-public"

# Konuk filtresi
guests = [
    "Nuri Çetin",
    "Kemal Ayça",
    "İlker Gümüşoluk",
    "Anlatan Adam",
    "Anlatanadam",
    "Alper Çelik",
    "Ömür Okumuş",
    "Erman Arıcasoy",
]

def get_spotify():
    return spotipy.Spotify(auth=session.get("token_info", {}).get("access_token"))

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

def save_queue(data):
    with open("queue.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_queue():
    if os.path.exists("queue.json"):
        with open("queue.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return []

@app.route("/")
def index():
    return redirect("/view_queue")

@app.route("/login")
def login():
    sp_oauth = SpotifyOAuth(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, scope=SCOPE)
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route("/callback")
def callback():
    sp_oauth = SpotifyOAuth(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI, scope=SCOPE)
    code = request.args.get("code")
    token_info = sp_oauth.get_access_token(code, as_dict=True)
    session["token_info"] = token_info
    return redirect("/view_queue")

@app.route("/load_podcast")
def load_podcast():
    try:
        sp = get_spotify()
        episodes = fetch_all_episodes(sp)

        # Filtre uygula
        filtered = []
        for ep in episodes:
            title = ep.get("name", "")
            if any(g.lower() in title.lower() for g in guests):
                filtered.append({
                    "id": ep["id"],
                    "name": title,
                    "release_date": ep.get("release_date"),
                    "uri": ep.get("uri")
                })

        # Tarihe göre eskiden yeniye sırala
        filtered.sort(key=lambda x: x["release_date"])

        # Kuyruğu kaydet
        save_queue(filtered)

        return {"queued": len(filtered), "total": len(episodes)}
    except Exception as e:
        return {"error": str(e)}

@app.route("/view_queue")
def view_queue():
    try:
        queue = load_queue()
        if not queue:
            return "queue.json boş görünüyor!"
        out = "Podcast Queue\n"
        for ep in queue:
            out += f"{ep['name']} ({ep['release_date']}) - Not Played\n"
        return out
    except Exception as e:
        return f"Hata: {e}"

if _name_ == "_main_":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
