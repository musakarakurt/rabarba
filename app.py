import os
import json
import re
from flask import Flask, redirect, request
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Flask app
app = Flask(__name__)

# Spotify credentials
CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIPY_REDIRECT_URI")
SHOW_ID = os.getenv("SPOTIFY_SHOW_ID")  # Podcast ID
SCOPE = "user-library-read playlist-modify-public playlist-modify-private"

# Queue file
QUEUE_FILE = "queue.json"

# Guests to include
GUESTS = ["anlatan adam", "anlatanadam", "kemal ayça", "nuri çetin", "ilker gümüşoluk", "eda nur hancı", "barış akyüz", "erman arıcasoy", "firuze özdemir", "caner dağlı", "rozerin aydın", "elif gizem aykul", "beyza arslan", "seçil buket akıncı", "doğan tunçel", "can kılcıoğlu", "vildan atasever erdem", "doğan akdoğan", "alper çelik", "berk türkmani", "beyza şen", "merve polat", "deniz akbaba", "aslı tüter"]

# ---- Helpers ----
def get_spotify():
    return spotipy.Spotify(auth_manager=SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE
    ))

def fetch_all_episodes(sp):
    all_eps = []
    offset = 0
    limit = 50
    trid = SHOW_ID
    while True:
        res = sp.show_episodes(trid, limit=limit, offset=offset)
        items = res.get("items", []) or []
        items = [it for it in items if isinstance(it, dict)]
        all_eps.extend(items)
        if len(items) < limit:
            break
        offset += limit
    return all_eps

def filter_episodes(episodes):
    filtered = []
    for ep in episodes:
        name = ep.get("name", "").lower()
        desc = ep.get("description", "").lower()

        # Bölüm numarasını yakala
        match = re.search(r"(\d{1,4})", ep.get("name", ""))
        if match:
            num = int(match.group(1))
        else:
            num = 0

        # Konuk filtresi
        if any(g in name or g in desc for g in GUESTS):
            ep["_num"] = num
            filtered.append(ep)

    # Numara + ad sıralaması
    filtered.sort(key=lambda x: (x.get("_num", 0), x.get("name", "")))
    return filtered

def save_queue(data):
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_queue():
    if not os.path.exists(QUEUE_FILE):
        return []
    with open(QUEUE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# ---- Routes ----
@app.route("/")
def index():
    return redirect("/view_queue")

@app.route("/load_podcast")
def load_podcast():
    try:
        sp = get_spotify()
        episodes = fetch_all_episodes(sp)
        filtered = filter_episodes(episodes)
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
        out = ["Podcast Queue"]
        for ep in queue:
            out.append(f"{ep.get('name')} ({ep.get('release_date')})")
        return "<br>".join(out)
    except Exception as e:
        return f"Hata: {e}"

# ---- Run ----
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
